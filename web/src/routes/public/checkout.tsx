import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Copy, CreditCard, Loader2, QrCode, TimerOff } from 'lucide-react'
import type { Route } from './+types/checkout'
import { Button } from '@/components/ui/button'
import { ErrorState, Loading } from '@/components/common'
import { api } from '@/lib/api'
import { dateTime, money } from '@/lib/format'
import { asLang, t, useLang } from '@/lib/i18n'
import { useSession } from '@/lib/session-context'
import type { Booking, Payment } from '@/lib/types'
import { cn } from '@/lib/utils'

export function meta({ params }: Route.MetaArgs) {
  return [{ title: t(asLang(params.lang), 'checkout.title') }, { name: 'robots', content: 'noindex' }]
}

function Countdown({ until, onExpire }: { until: string; onExpire: () => void }) {
  const [left, setLeft] = useState(() => new Date(until).getTime() - Date.now())
  useEffect(() => {
    const id = setInterval(() => {
      const ms = new Date(until).getTime() - Date.now()
      setLeft(ms)
      if (ms <= 0) {
        clearInterval(id)
        onExpire()
      }
    }, 1000)
    return () => clearInterval(id)
  }, [until, onExpire])
  const s = Math.max(0, Math.floor(left / 1000))
  return <span className="font-mono font-semibold tabular-nums">{String(Math.floor(s / 60)).padStart(2, '0')}:{String(s % 60).padStart(2, '0')}</span>
}

export default function Checkout() {
  const lang = useLang()
  const { code } = useParams()
  const s = useSession()
  const qc = useQueryClient()
  const [method, setMethod] = useState<'pix' | 'card'>('pix')
  const [copied, setCopied] = useState(false)
  const [expired, setExpired] = useState(false)

  const booking = useQuery({
    queryKey: ['booking', code],
    queryFn: () => api<Booking>(`/bookings/${code}`),
    enabled: s.ready,
    refetchInterval: (q) => (q.state.data?.status === 'held' ? 3000 : false),
  })
  const b = booking.data
  const pending = b?.payments.find((p) => p.status === 'pending')

  const pay = useMutation({
    mutationFn: () => api<{ payment: Payment; booking: Booking }>(`/bookings/${code}/payments`, {
      method: 'POST', body: { method, idempotency_key: `${code}-${method}` },
    }),
    onSuccess: (r) => {
      qc.setQueryData(['booking', code], r.booking)
      if (r.payment.checkout_url) window.location.href = r.payment.checkout_url
    },
  })
  const simulate = useMutation({
    mutationFn: (chargeId: string) => api<Booking>(`/dev/payments/${chargeId}/simulate`, { method: 'POST' }),
    onSuccess: (r) => qc.setQueryData(['booking', code], r),
  })

  if (!s.ready || booking.isLoading) return <div className="mx-auto max-w-xl px-4 py-10"><Loading label={t(lang, 'common.loading')} /></div>
  if (booking.error || !b) return <div className="mx-auto max-w-xl px-4 py-10"><ErrorState error={booking.error} /></div>

  const isConfirmed = ['confirmed', 'completed'].includes(b.status)
  const isDead = expired || ['expired', 'cancelled'].includes(b.status)

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <h1 className="mb-1 text-2xl font-semibold">{isConfirmed ? t(lang, 'checkout.confirmed') : t(lang, 'checkout.title')}</h1>
      <div className="mb-6 rounded-xl border bg-card p-4 text-sm">
        <div className="font-semibold">{b.title}</div>
        <div className="text-muted-foreground">{dateTime(b.starts_at, lang)} · {b.items.map((i) => `${i.quantity}× ${i.label}`).join(', ')}</div>
        <div className="mt-2 flex justify-between border-t pt-2">
          <span>{t(lang, 'tour.total')}</span><span className="font-semibold">{money(b.total_cents, lang)}</span>
        </div>
      </div>

      {isConfirmed && (
        <div className="space-y-4 rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
          <CheckCircle2 className="mx-auto size-10 text-emerald-600" />
          <p>{t(lang, 'checkout.confirmedText')}</p>
          <p className="font-mono text-lg font-semibold">{b.code}</p>
          <Button asChild><Link to={`/${lang}/reservas/${b.code}`}>{t(lang, 'checkout.seeBooking')}</Link></Button>
        </div>
      )}

      {!isConfirmed && isDead && (
        <div className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <TimerOff className="mx-auto size-8 text-amber-600" />
          <p>{t(lang, 'checkout.expired')}</p>
          <Button asChild variant="outline"><Link to={`/${lang}/passeios/${b.tour_slug}`}>{t(lang, 'common.back')}</Link></Button>
        </div>
      )}

      {!isConfirmed && !isDead && b.status === 'held' && (
        <div className="space-y-5">
          {b.hold_expires_at && (
            <p className="text-sm">{t(lang, 'checkout.holdFor')} <Countdown until={b.hold_expires_at} onExpire={() => setExpired(true)} /></p>
          )}

          {!pending && (
            <>
              <fieldset>
                <legend className="mb-2 text-sm font-semibold">{t(lang, 'checkout.method')}</legend>
                <div className="grid grid-cols-2 gap-3">
                  {(['pix', 'card'] as const).map((m) => (
                    <button key={m} type="button" onClick={() => setMethod(m)} aria-pressed={method === m}
                      className={cn('flex items-center justify-center gap-2 rounded-lg border p-4 text-sm', method === m ? 'border-primary bg-primary/10 font-semibold text-primary' : 'hover:border-primary')}>
                      {m === 'pix' ? <QrCode className="size-5" /> : <CreditCard className="size-5" />}
                      {t(lang, m === 'pix' ? 'checkout.pix' : 'checkout.card')}
                    </button>
                  ))}
                </div>
              </fieldset>
              {method === 'card' && <p className="text-xs text-muted-foreground">{t(lang, 'checkout.cardNote')}</p>}
              {pay.error && <ErrorState error={pay.error} />}
              <Button size="lg" className="w-full" disabled={pay.isPending} onClick={() => pay.mutate()}>
                {pay.isPending && <Loader2 className="animate-spin" />} {t(lang, 'checkout.pay')} {money(b.total_cents, lang)}
              </Button>
            </>
          )}

          {pending && (
            <div className="space-y-4 rounded-xl border bg-card p-5">
              {pending.method === 'pix' && pending.pix_qr_code && (
                <>
                  <p className="text-sm">{t(lang, 'checkout.pixCopy')}</p>
                  <div className="flex gap-2">
                    <input readOnly value={pending.pix_qr_code} aria-label="Pix" className="h-9 flex-1 truncate rounded-md border bg-muted px-2 font-mono text-xs" />
                    <Button type="button" variant="outline" onClick={() => {
                      navigator.clipboard?.writeText(pending.pix_qr_code ?? '')
                      setCopied(true)
                      setTimeout(() => setCopied(false), 2000)
                    }}>
                      <Copy /> {copied ? t(lang, 'checkout.copied') : t(lang, 'checkout.copy')}
                    </Button>
                  </div>
                </>
              )}
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />{t(lang, 'checkout.waiting')}</p>
              {s.config?.payment_gateway === 'fake' && (
                <Button variant="secondary" className="w-full border border-dashed border-amber-400" disabled={simulate.isPending}
                  onClick={() => simulate.mutate(pending.charge_id)}>
                  {t(lang, 'checkout.simulate')}
                </Button>
              )}
              {simulate.error && <ErrorState error={simulate.error} />}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

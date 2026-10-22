import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, ExternalLink, MapPin, Phone } from 'lucide-react'
import type { Route } from './+types/booking'
import { Button } from '@/components/ui/button'
import { ErrorState, Loading, StatusBadge } from '@/components/common'
import { api, openFile } from '@/lib/api'
import { dateTime, money } from '@/lib/format'
import { asLang, t, useLang, type TKey } from '@/lib/i18n'
import { useSession } from '@/lib/session-context'
import type { Booking } from '@/lib/types'

export function meta({ params }: Route.MetaArgs) {
  return [{ title: `${t(asLang(params.lang), 'booking.code')} ${params.code}` }, { name: 'robots', content: 'noindex' }]
}

export default function BookingPage() {
  const lang = useLang()
  const { code } = useParams()
  const s = useSession()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['booking', code], queryFn: () => api<Booking>(`/bookings/${code}`), enabled: s.ready })
  const cancel = useMutation({
    mutationFn: () => api<Booking>(`/bookings/${code}/cancel`, { method: 'POST' }),
    onSuccess: (b) => {
      qc.setQueryData(['booking', code], b)
      qc.invalidateQueries({ queryKey: ['my-bookings'] })
    },
  })

  if (!s.ready || q.isLoading) return <div className="mx-auto max-w-2xl px-4 py-10"><Loading label={t(lang, 'common.loading')} /></div>
  if (q.error || !q.data) return <div className="mx-auto max-w-2xl px-4 py-10"><ErrorState error={q.error} /></div>
  const b = q.data
  const p = b.private

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link to={`/${lang}/reservas`} className="text-sm text-muted-foreground hover:underline">← {t(lang, 'nav.bookings')}</Link>
      <div className="mt-3 mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{b.title}</h1>
          <p className="text-muted-foreground">{b.area}</p>
        </div>
        <StatusBadge status={b.status} label={t(lang, `status.${b.status}` as TKey)} />
      </div>

      <dl className="grid gap-4 rounded-xl border bg-card p-5 text-sm sm:grid-cols-2">
        <div><dt className="text-muted-foreground">{t(lang, 'booking.code')}</dt><dd className="font-mono font-semibold">{b.code}</dd></div>
        <div><dt className="text-muted-foreground">{t(lang, 'booking.when')}</dt><dd className="font-medium capitalize">{dateTime(b.starts_at, lang)}</dd></div>
        <div><dt className="text-muted-foreground">{t(lang, 'booking.people')}</dt><dd>{b.items.map((i) => `${i.quantity}× ${i.label}`).join(', ')}</dd></div>
        <div><dt className="text-muted-foreground">{t(lang, 'tour.total')}</dt><dd className="font-semibold">{money(b.total_cents, lang)}</dd></div>
        {b.refund_amount_cents > 0 && (
          <div><dt className="text-muted-foreground">{t(lang, 'booking.refund')}</dt><dd>{money(b.refund_amount_cents, lang)}</dd></div>
        )}
        {b.on_site_fees_note && (
          <div className="sm:col-span-2"><dt className="text-muted-foreground">{t(lang, 'tour.fees')}</dt><dd>{b.on_site_fees_note}</dd></div>
        )}
      </dl>

      {p && (
        <section className="mt-6 space-y-3 rounded-xl border bg-card p-5 text-sm">
          <h2 className="font-semibold">{t(lang, 'booking.meeting')}</h2>
          <p className="flex items-start gap-2"><MapPin className="mt-0.5 size-4 shrink-0 text-primary" />
            <span>{p.meeting_point_address}{p.meeting_point_details && <><br /><span className="text-muted-foreground">{p.meeting_point_details}</span></>}</span>
          </p>
          {p.meeting_lat !== null && (
            <a className="inline-flex items-center gap-1 text-primary underline" target="_blank" rel="noreferrer"
              href={`https://www.google.com/maps?q=${p.meeting_lat},${p.meeting_lng}`}>
              {t(lang, 'booking.openMap')} <ExternalLink className="size-3" />
            </a>
          )}
          <h2 className="pt-2 font-semibold">{t(lang, 'booking.operator')}</h2>
          <p>{p.operator_trade_name}</p>
          {p.operator_phone && (
            <p className="flex items-center gap-2"><Phone className="size-4 text-primary" />
              <a className="underline" href={`https://wa.me/${p.operator_phone.replace(/\D/g, '')}`} target="_blank" rel="noreferrer">{p.operator_phone}</a>
            </p>
          )}
        </section>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        {b.status === 'held' && <Button asChild><Link to={`/${lang}/checkout/${b.code}`}>{t(lang, 'booking.pay')}</Link></Button>}
        {['confirmed', 'completed'].includes(b.status) && (
          <Button onClick={() => openFile(`/bookings/${b.code}/voucher`)}><Download /> {t(lang, 'booking.voucher')}</Button>
        )}
        {b.status === 'confirmed' && (
          <Button variant="outline" disabled={cancel.isPending} onClick={() => {
            if (window.confirm(`${t(lang, 'booking.cancelConfirm')} ${money(b.refund_if_cancelled_now_cents ?? 0, lang)}`)) cancel.mutate()
          }}>
            {t(lang, 'booking.cancel')}
          </Button>
        )}
      </div>
      {b.status === 'confirmed' && (
        <p className="mt-2 text-xs text-muted-foreground">{t(lang, 'tour.policy')}: {t(lang, `tour.policy.${b.cancellation_policy}` as TKey)}</p>
      )}
      {cancel.error && <div className="mt-3"><ErrorState error={cancel.error} /></div>}
    </div>
  )
}

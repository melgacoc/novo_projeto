import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import type { Route } from './+types/my-bookings'
import { Empty, ErrorState, Loading, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { dateTime, money } from '@/lib/format'
import { asLang, t, useLang, type TKey } from '@/lib/i18n'
import { useSession } from '@/lib/session-context'
import type { Booking, Page } from '@/lib/types'

export function meta({ params }: Route.MetaArgs) {
  return [{ title: t(asLang(params.lang), 'nav.bookings') }, { name: 'robots', content: 'noindex' }]
}

export default function MyBookings() {
  const lang = useLang()
  const s = useSession()
  const needsLogin = s.ready && s.authEnabled && !s.me
  const q = useQuery({
    queryKey: ['my-bookings'],
    queryFn: () => api<Page<Booking>>('/bookings?page_size=50'),
    enabled: s.ready && !needsLogin,
  })
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">{t(lang, 'nav.bookings')}</h1>
      {needsLogin ? (
        <Button asChild><Link to={`/${lang}/entrar?next=/${lang}/reservas`}>{t(lang, 'nav.login')}</Link></Button>
      ) : q.isLoading || !s.ready ? (
        <Loading label={t(lang, 'common.loading')} />
      ) : q.error ? (
        <ErrorState error={q.error} />
      ) : !q.data?.items.length ? (
        <Empty>{t(lang, 'booking.none')} <Link className="text-primary underline" to={`/${lang}/passeios`}>{t(lang, 'nav.tours')}</Link></Empty>
      ) : (
        <ul className="space-y-3">
          {q.data.items.map((b) => (
            <li key={b.code}>
              <Link to={b.status === 'held' ? `/${lang}/checkout/${b.code}` : `/${lang}/reservas/${b.code}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4 hover:border-primary">
                <div>
                  <div className="font-semibold">{b.title}</div>
                  <div className="text-sm text-muted-foreground">{dateTime(b.starts_at, lang)} · {b.pax_total} · {money(b.total_cents, lang)}</div>
                </div>
                <StatusBadge status={b.status} label={t(lang, `status.${b.status}` as TKey)} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

import { Suspense, lazy, useMemo, useState } from 'react'
import { Link, data, useNavigate } from 'react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import { CalendarDays, CheckCircle2, Clock, Info, MapPin, ShieldCheck, Users } from 'lucide-react'
import type { Route } from './+types/tour'
import { Button } from '@/components/ui/button'
import { Counter, ErrorState, Field, Loading, Photo, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { ApiError, api } from '@/lib/api'
import { addDays, dateOnly, duration, money, todayRio } from '@/lib/format'
import { asLang, t, useLang } from '@/lib/i18n'
import { useSession } from '@/lib/session-context'
import type { Booking, DeparturePublic, TourDetail } from '@/lib/types'
import { cn } from '@/lib/utils'

const MapView = lazy(() => import('@/components/MapView').then((m) => ({ default: m.MapView })))

export async function loader({ params }: Route.LoaderArgs) {
  const lang = asLang(params.lang)
  try {
    const tour = await api<TourDetail>(`/tours/${params.slug}?locale=${lang}`)
    return { tour }
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) throw data(null, { status: 404 })
    throw e
  }
}

export function meta({ data: d, params }: Route.MetaArgs) {
  if (!d) return [{ title: 'Não encontrado' }]
  const { tour } = d
  return [
    { title: `${tour.title} · Rio de Janeiro` },
    { name: 'description', content: tour.summary },
    { property: 'og:title', content: tour.title },
    { property: 'og:description', content: tour.summary },
    ...(tour.photo ? [{ property: 'og:image', content: tour.photo }] : []),
    ...(['pt', 'es', 'en'] as const).map((l) => ({ tagName: 'link', rel: 'alternate', hrefLang: l, href: `/${l}/passeios/${params.slug}` })),
    {
      'script:ld+json': {
        '@context': 'https://schema.org',
        '@type': 'TouristTrip',
        name: tour.title,
        description: tour.summary,
        offers: tour.from_price_cents ? { '@type': 'Offer', price: tour.from_price_cents / 100, priceCurrency: 'BRL' } : undefined,
      },
    },
  ]
}

function lines(text: string) {
  return text.split('\n').map((l) => l.trim()).filter(Boolean)
}

function BookingWidget({ tour }: { tour: TourDetail }) {
  const lang = useLang()
  const s = useSession()
  const navigate = useNavigate()
  const [from] = useState(todayRio())
  const deps = useQuery({
    queryKey: ['departures', tour.slug, from],
    queryFn: () => api<DeparturePublic[]>(`/tours/${tour.slug}/departures?from=${from}&to=${addDays(from, 30)}`),
  })
  const dates = useMemo(() => {
    const map = new Map<string, DeparturePublic[]>()
    for (const d of deps.data ?? []) map.set(d.date, [...(map.get(d.date) ?? []), d])
    return [...map.entries()]
  }, [deps.data])
  const [date, setDate] = useState<string | null>(null)
  const activeDate = date ?? dates.find(([, ds]) => ds.some((d) => d.availability !== 'sold_out'))?.[0] ?? null
  const times = dates.find(([d]) => d === activeDate)?.[1] ?? []
  const [depId, setDepId] = useState<number | null>(null)
  const activeDep = times.find((d) => d.id === depId) ?? times.find((d) => d.availability !== 'sold_out') ?? null

  const [qty, setQty] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {}
    tour.price_categories.forEach((c) => (init[c.code] = c.code === 'adult' ? Math.max(1, tour.min_pax_per_booking) : 0))
    if (!tour.price_categories.some((c) => c.code === 'adult') && tour.price_categories[0]) init[tour.price_categories[0].code] = 1
    return init
  })
  const pax = Object.values(qty).reduce((a, b) => a + b, 0)

  const quote = useQuery({
    queryKey: ['quote', activeDep?.id, qty],
    queryFn: () => api<{ total_cents: number }>('/quotes', { method: 'POST', body: { departure_id: activeDep!.id, quantities: qty }, locale: lang }),
    enabled: !!activeDep && pax > 0,
    retry: false,
  })

  const [step, setStep] = useState<'choose' | 'contact'>('choose')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const create = useMutation({
    mutationFn: () =>
      api<Booking>('/bookings', {
        method: 'POST',
        body: { departure_id: activeDep!.id, quantities: qty, contact_name: name || s.me?.name, contact_phone: phone || s.me?.phone, locale: lang },
      }),
    onSuccess: (b) => navigate(`/${lang}/checkout/${b.code}`),
  })

  const needsLogin = s.authEnabled && !s.me
  const nameValue = name || s.me?.name || ''
  const phoneValue = phone || s.me?.phone || ''

  return (
    <div className="space-y-5 rounded-xl border bg-card p-5 shadow-sm">
      <div>
        <div className="text-xs text-muted-foreground">{t(lang, 'card.from')}</div>
        <div className="text-2xl font-bold text-primary">{money(tour.from_price_cents, lang)}</div>
        {tour.instant_booking && (
          <p className="mt-1 flex items-center gap-1 text-xs text-emerald-700"><CheckCircle2 className="size-3.5" />{t(lang, 'tour.instant')}</p>
        )}
      </div>

      {step === 'choose' && (
        <>
          <div>
            <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><CalendarDays className="size-4" />{t(lang, 'tour.chooseDate')}</h3>
            {deps.isLoading ? <Loading label={t(lang, 'common.loading')} /> : dates.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t(lang, 'tour.noDepartures')}</p>
            ) : (
              <div className="flex gap-2 overflow-x-auto pb-1">
                {dates.map(([d, ds]) => {
                  const soldOut = ds.every((x) => x.availability === 'sold_out')
                  return (
                    <button key={d} type="button" disabled={soldOut}
                      onClick={() => { setDate(d); setDepId(null) }}
                      aria-pressed={d === activeDate}
                      className={cn('shrink-0 rounded-lg border px-3 py-2 text-sm capitalize', d === activeDate ? 'border-primary bg-primary/10 font-semibold text-primary' : 'hover:border-primary', soldOut && 'opacity-40 line-through')}>
                      {dateOnly(d, lang)}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {times.length > 0 && (
            <div>
              <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><Clock className="size-4" />{t(lang, 'tour.chooseTime')}</h3>
              <div className="flex flex-wrap gap-2">
                {times.map((d) => (
                  <button key={d.id} type="button" disabled={d.availability === 'sold_out'} onClick={() => setDepId(d.id)}
                    aria-pressed={d.id === activeDep?.id}
                    className={cn('rounded-lg border px-3 py-2 text-sm', d.id === activeDep?.id ? 'border-primary bg-primary/10 font-semibold text-primary' : 'hover:border-primary', d.availability === 'sold_out' && 'opacity-40')}>
                    {d.time}
                    <span className={cn('ml-2 text-xs', d.availability === 'last_seats' ? 'text-orange-600' : 'text-muted-foreground')}>
                      {t(lang, `avail.${d.availability}`)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div>
            <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><Users className="size-4" />{t(lang, 'tour.people')}</h3>
            <div className="space-y-2">
              {tour.price_categories.map((c) => (
                <div key={c.code} className="flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <div className="font-medium">{c.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {c.code !== 'adult' && `${c.min_age}–${c.max_age} ${t(lang, 'tour.age')} · `}
                      {c.price_cents_today === 0 ? t(lang, 'tour.free') : money(c.price_cents_today, lang)}
                    </div>
                  </div>
                  <Counter label={c.label} value={qty[c.code] ?? 0} max={tour.max_pax_per_booking}
                    onChange={(v) => setQty({ ...qty, [c.code]: v })} />
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between border-t pt-4">
            <span className="text-sm text-muted-foreground">{t(lang, 'tour.total')}</span>
            <span className="text-xl font-bold">{quote.data ? money(quote.data.total_cents, lang) : '—'}</span>
          </div>
          {quote.error && <p className="text-sm text-destructive">{errorMessage(quote.error)}</p>}

          {needsLogin ? (
            <Button asChild className="w-full" size="lg">
              <Link to={`/${lang}/entrar?next=${encodeURIComponent(`/${lang}/passeios/${tour.slug}`)}`}>{t(lang, 'tour.loginToBook')}</Link>
            </Button>
          ) : (
            <Button className="w-full" size="lg" disabled={!activeDep || !quote.data} onClick={() => setStep('contact')}>
              {t(lang, 'tour.book')}
            </Button>
          )}
        </>
      )}

      {step === 'contact' && (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); create.mutate() }}>
          <h3 className="font-semibold">{t(lang, 'tour.yourData')}</h3>
          <p className="text-sm text-muted-foreground">
            {activeDep && `${dateOnly(activeDep.date, lang)} · ${activeDep.time}`} · {pax} · {quote.data && money(quote.data.total_cents, lang)}
          </p>
          <Field label={t(lang, 'tour.name')} htmlFor="c-name">
            <input id="c-name" required minLength={2} value={nameValue} onChange={(e) => setName(e.target.value)} className={inputClass} autoComplete="name" />
          </Field>
          <Field label={t(lang, 'tour.phone')} htmlFor="c-phone" hint="+56 9 1234 5678 · +54 9 11 1234 5678 · 21 99999 9999">
            <input id="c-phone" required value={phoneValue} onChange={(e) => setPhone(e.target.value)} className={inputClass} autoComplete="tel" inputMode="tel" />
          </Field>
          {create.error && <ErrorState error={create.error} />}
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => setStep('choose')}>{t(lang, 'common.back')}</Button>
            <Button type="submit" className="flex-1" disabled={create.isPending}>{t(lang, 'tour.continue')}</Button>
          </div>
        </form>
      )}
    </div>
  )
}

export default function TourPage({ loaderData }: Route.ComponentProps) {
  const lang = useLang()
  const { tour } = loaderData
  const [photo, setPhoto] = useState(0)
  const policy = `tour.policy.${tour.cancellation_policy}` as const

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <nav className="mb-4 text-sm text-muted-foreground">
        <Link to={`/${lang}/passeios`} className="hover:underline">{t(lang, 'nav.tours')}</Link>
        {tour.category && <> / <Link to={`/${lang}/passeios?category=${tour.category.slug}`} className="hover:underline">{tour.category.name}</Link></>}
      </nav>
      <h1 className="text-2xl font-bold sm:text-3xl">{tour.title}</h1>
      <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span className="flex items-center gap-1"><MapPin className="size-4" />{tour.area}</span>
        <span className="flex items-center gap-1"><Clock className="size-4" />{duration(tour.duration_minutes, lang)}</span>
        {tour.operator_name && <span>{t(lang, 'card.by')} {tour.operator_name}</span>}
      </p>

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_380px]">
        <div className="space-y-8">
          <div>
            <Photo src={tour.photos[photo]?.url ?? tour.photo} alt={tour.title} className="aspect-[3/2] w-full rounded-xl" />
            {tour.photos.length > 1 && (
              <div className="mt-2 flex gap-2">
                {tour.photos.map((p, i) => (
                  <button key={p.url} type="button" onClick={() => setPhoto(i)} aria-label={`Foto ${i + 1}`}
                    className={cn('overflow-hidden rounded-md border-2', i === photo ? 'border-primary' : 'border-transparent')}>
                    <img src={p.url} alt="" className="h-14 w-20 object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <section>
            <h2 className="mb-2 text-lg font-semibold">{t(lang, 'tour.about')}</h2>
            <p className="whitespace-pre-line leading-relaxed">{tour.description}</p>
          </section>

          <div className="grid gap-6 sm:grid-cols-2">
            {tour.includes && (
              <section>
                <h2 className="mb-2 font-semibold">{t(lang, 'tour.includes')}</h2>
                <ul className="space-y-1 text-sm">{lines(tour.includes).map((l) => <li key={l} className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />{l}</li>)}</ul>
              </section>
            )}
            {tour.excludes && (
              <section>
                <h2 className="mb-2 font-semibold">{t(lang, 'tour.excludes')}</h2>
                <ul className="list-disc space-y-1 pl-5 text-sm">{lines(tour.excludes).map((l) => <li key={l}>{l}</li>)}</ul>
              </section>
            )}
          </div>

          {tour.what_to_bring && (
            <section>
              <h2 className="mb-2 font-semibold">{t(lang, 'tour.bring')}</h2>
              <p className="text-sm">{tour.what_to_bring}</p>
            </section>
          )}

          <section className="space-y-2 rounded-xl border bg-card p-4 text-sm">
            <p className="flex items-start gap-2"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" /><span><strong>{t(lang, 'tour.policy')}:</strong> {t(lang, policy)}</span></p>
            {tour.on_site_fees_note && (
              <p className="flex items-start gap-2"><Info className="mt-0.5 size-4 shrink-0 text-primary" /><span><strong>{t(lang, 'tour.fees')}:</strong> {tour.on_site_fees_note}</span></p>
            )}
          </section>

          {tour.lat !== null && tour.lng !== null && (
            <section>
              <h2 className="mb-1 font-semibold">{t(lang, 'tour.area')}: {tour.area}</h2>
              <p className="mb-3 text-sm text-muted-foreground">{t(lang, 'tour.areaNote')}</p>
              <Suspense fallback={<div className="h-64 rounded-xl bg-muted" />}>
                <MapView className="h-64 w-full rounded-xl border" approximate zoom={13}
                  points={[{ id: tour.id, lat: tour.lat, lng: tour.lng, label: tour.area }]} />
              </Suspense>
            </section>
          )}
        </div>

        <div className="lg:sticky lg:top-20 lg:self-start">
          <BookingWidget tour={tour} />
        </div>
      </div>
    </div>
  )
}

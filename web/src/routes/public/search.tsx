import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { Form, Link, useNavigate, useNavigation, useSearchParams } from 'react-router'
import { List, LocateFixed, Map as MapIcon, Search, X } from 'lucide-react'
import type { Route } from './+types/search'
import { Button } from '@/components/ui/button'
import { Empty, Field, Loading, TourCard, inputClass } from '@/components/common'
import { api } from '@/lib/api'
import { asLang, t, useLang } from '@/lib/i18n'
import { money } from '@/lib/format'
import type { Category, Page, TourCard as TourCardT } from '@/lib/types'

const MapView = lazy(() => import('@/components/MapView').then((m) => ({ default: m.MapView })))

const FILTERS = ['q', 'category', 'date', 'time_from', 'time_to', 'price_max', 'available', 'pax', 'lat', 'lng', 'radius_km', 'sort', 'page', 'near']

export async function loader({ params, request }: Route.LoaderArgs) {
  const lang = asLang(params.lang)
  const url = new URL(request.url)
  const qs = new URLSearchParams({ locale: lang, page_size: '24' })
  for (const k of FILTERS) {
    const v = url.searchParams.get(k)
    if (!v || k === 'near') continue
    if (k === 'price_max') qs.set(k, String(Math.round(Number(v) * 100)))
    else qs.set(k, v)
  }
  const [result, categories] = await Promise.all([
    api<Page<TourCardT>>(`/tours?${qs}`),
    api<Category[]>(`/categories?locale=${lang}`),
  ])
  return { result, categories }
}

export function meta({ params }: Route.MetaArgs) {
  const lang = asLang(params.lang)
  return [{ title: `${t(lang, 'search.title')} · Rio de Janeiro` }, { name: 'description', content: t(lang, 'home.subtitle') }]
}

type GeoResult = { label: string; lat: number; lng: number }

function AddressSearch({ onPick }: { onPick: (r: GeoResult) => void }) {
  const lang = useLang()
  const [q, setQ] = useState('')
  const [results, setResults] = useState<GeoResult[]>([])
  useEffect(() => {
    if (q.trim().length < 3) return
    const ctrl = new AbortController()
    const id = setTimeout(() => {
      api<GeoResult[]>(`/geocode?q=${encodeURIComponent(q)}&locale=${lang}`, { signal: ctrl.signal })
        .then(setResults)
        .catch(() => setResults([]))
    }, 400)
    return () => {
      clearTimeout(id)
      ctrl.abort()
    }
  }, [q, lang])
  return (
    <div className="relative">
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t(lang, 'search.address')}
        aria-label={t(lang, 'search.address')} className={inputClass} />
      {q.trim().length >= 3 && results.length > 0 && (
        <ul className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-md border bg-popover text-sm shadow-lg">
          {results.map((r, i) => (
            <li key={i}>
              <button type="button" className="w-full px-3 py-2 text-left hover:bg-accent"
                onClick={() => {
                  onPick(r)
                  setQ('')
                  setResults([])
                }}>
                {r.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function SearchPage({ loaderData }: Route.ComponentProps) {
  const lang = useLang()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const navigation = useNavigation()
  const view = params.get('view') === 'map' ? 'map' : 'list'
  const { result, categories } = loaderData
  const lat = params.get('lat')
  const lng = params.get('lng')
  const center = lat && lng ? { lat: Number(lat), lng: Number(lng) } : null
  const [geoError, setGeoError] = useState(false)

  function setNear(latV: number, lngV: number, label: string) {
    const next = new URLSearchParams(params)
    next.set('lat', latV.toFixed(5))
    next.set('lng', lngV.toFixed(5))
    next.set('radius_km', next.get('radius_km') ?? '15')
    next.set('sort', 'distance')
    next.set('near', label)
    setParams(next)
  }

  function nearMe() {
    navigator.geolocation?.getCurrentPosition(
      (p) => setNear(p.coords.latitude, p.coords.longitude, t(lang, 'home.near')),
      () => setGeoError(true),
      { timeout: 8000 },
    )
  }

  function clearNear() {
    const next = new URLSearchParams(params)
    for (const k of ['lat', 'lng', 'radius_km', 'near']) next.delete(k)
    if (next.get('sort') === 'distance') next.delete('sort')
    setParams(next)
  }

  function setView(v: 'list' | 'map') {
    const next = new URLSearchParams(params)
    next.set('view', v)
    setParams(next, { preventScrollReset: true })
  }

  const points = useMemo(() => result.items
    .filter((tour) => tour.lat !== null && tour.lng !== null)
    .map((tour) => ({
      id: tour.id,
      lat: tour.lat as number,
      lng: tour.lng as number,
      label: money(tour.from_price_cents, lang).replace(/,00$/, '').replace(/\.00$/, ''),
      href: `/${lang}/passeios/${tour.slug}`,
    })), [result.items, lang])

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">{t(lang, 'search.title')}</h1>
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside>
          <Form method="get" className="space-y-4 rounded-xl border bg-card p-4" key={params.toString()}>
            {['lat', 'lng', 'radius_km', 'near', 'view'].map((k) => params.get(k) && <input key={k} type="hidden" name={k} value={params.get(k) ?? ''} />)}
            <Field label={t(lang, 'search.q')} htmlFor="f-q">
              <input id="f-q" name="q" defaultValue={params.get('q') ?? ''} className={inputClass} />
            </Field>
            <Field label={t(lang, 'search.category')} htmlFor="f-cat">
              <select id="f-cat" name="category" defaultValue={params.get('category') ?? ''} className={inputClass}>
                <option value="">{t(lang, 'search.allCategories')}</option>
                {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
              </select>
            </Field>
            <Field label={t(lang, 'search.date')} htmlFor="f-date">
              <input id="f-date" type="date" name="date" defaultValue={params.get('date') ?? ''} className={inputClass} />
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label={t(lang, 'search.timeFrom')} htmlFor="f-tf">
                <input id="f-tf" type="time" name="time_from" defaultValue={params.get('time_from') ?? ''} className={inputClass} />
              </Field>
              <Field label={t(lang, 'search.timeTo')} htmlFor="f-tt">
                <input id="f-tt" type="time" name="time_to" defaultValue={params.get('time_to') ?? ''} className={inputClass} />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Field label={t(lang, 'search.priceMax')} htmlFor="f-pm">
                <input id="f-pm" type="number" min={0} name="price_max" defaultValue={params.get('price_max') ?? ''} className={inputClass} />
              </Field>
              <Field label={t(lang, 'search.people')} htmlFor="f-pax">
                <input id="f-pax" type="number" min={1} max={50} name="pax" defaultValue={params.get('pax') ?? ''} className={inputClass} />
              </Field>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" name="available" value="true" defaultChecked={params.get('available') === 'true'} />
              {t(lang, 'search.available')}
            </label>
            <Field label={t(lang, 'search.sort')} htmlFor="f-sort">
              <select id="f-sort" name="sort" defaultValue={params.get('sort') ?? 'relevance'} className={inputClass}>
                <option value="relevance">{t(lang, 'search.sort.relevance')}</option>
                <option value="price">{t(lang, 'search.sort.price')}</option>
                {center && <option value="distance">{t(lang, 'search.sort.distance')}</option>}
              </select>
            </Field>
            <div className="flex gap-2">
              <Button type="submit" className="flex-1"><Search /> {t(lang, 'search.apply')}</Button>
              <Button type="button" variant="outline" onClick={() => navigate(`/${lang}/passeios`)}>{t(lang, 'search.clear')}</Button>
            </div>
          </Form>
        </aside>

        <section aria-busy={navigation.state === 'loading'}>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <div className="min-w-56 flex-1"><AddressSearch onPick={(r) => setNear(r.lat, r.lng, r.label.split(',')[0])} /></div>
            <Button type="button" variant="outline" onClick={nearMe}><LocateFixed /> {t(lang, 'home.near')}</Button>
            <div className="flex overflow-hidden rounded-md border" role="group">
              <Button type="button" variant={view === 'list' ? 'default' : 'ghost'} className="rounded-none" onClick={() => setView('list')} aria-pressed={view === 'list'}><List /> {t(lang, 'search.list')}</Button>
              <Button type="button" variant={view === 'map' ? 'default' : 'ghost'} className="rounded-none" onClick={() => setView('map')} aria-pressed={view === 'map'}><MapIcon /> {t(lang, 'search.map')}</Button>
            </div>
          </div>
          {geoError && <p className="mb-3 text-sm text-destructive">{t(lang, 'search.geoDenied')}</p>}
          {params.get('near') && (
            <p className="mb-3 flex items-center gap-2 text-sm">
              {t(lang, 'search.near')} <strong>{params.get('near')}</strong> ({params.get('radius_km')} km)
              <button type="button" onClick={clearNear} aria-label={t(lang, 'search.clear')} className="rounded p-0.5 hover:bg-accent"><X className="size-4" /></button>
            </p>
          )}
          <p className="mb-4 text-sm text-muted-foreground">{result.total} {t(lang, 'search.results')}</p>

          {view === 'map' && (
            <div className="mb-6">
              <Suspense fallback={<Loading label={t(lang, 'common.loading')} />}>
                <MapView className="h-[28rem] w-full rounded-xl border" points={points} center={center} zoom={center ? 12 : 10}
                  onPointClick={(p) => p.href && navigate(p.href)} />
              </Suspense>
            </div>
          )}

          {result.items.length === 0 ? (
            <Empty>{t(lang, 'search.none')}</Empty>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {result.items.map((tour) => <TourCard key={tour.id} tour={tour} lang={lang} />)}
            </div>
          )}
          {result.total > result.page * result.page_size && (
            <div className="mt-6 text-center">
              <Link to={`?${new URLSearchParams({ ...Object.fromEntries(params), page: String(result.page + 1) })}`} className="text-primary underline">
                {t(lang, 'search.more')}
              </Link>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

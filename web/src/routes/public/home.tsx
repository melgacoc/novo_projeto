import { useState } from 'react'
import { Form, Link, useNavigate } from 'react-router'
import { LocateFixed, Search } from 'lucide-react'
import type { Route } from './+types/home'
import { Button } from '@/components/ui/button'
import { TourCard, inputClass } from '@/components/common'
import { api } from '@/lib/api'
import { asLang, t, useLang } from '@/lib/i18n'
import { todayRio } from '@/lib/format'
import type { Category, Page, TourCard as TourCardT } from '@/lib/types'

export async function loader({ params }: Route.LoaderArgs) {
  const lang = asLang(params.lang)
  const [categories, featured, today] = await Promise.all([
    api<Category[]>(`/categories?locale=${lang}`),
    api<Page<TourCardT>>(`/tours?locale=${lang}&page_size=8`),
    api<Page<TourCardT>>(`/tours?locale=${lang}&page_size=4&available=true&date=${todayRio()}`),
  ])
  return { categories, featured: featured.items, today: today.items }
}

export function meta({ params }: Route.MetaArgs) {
  const lang = asLang(params.lang)
  return [
    { title: t(lang, 'home.title') },
    { name: 'description', content: t(lang, 'home.subtitle') },
    { property: 'og:title', content: t(lang, 'home.title') },
    ...(['pt', 'es', 'en'] as const).map((l) => ({ tagName: 'link', rel: 'alternate', hrefLang: l, href: `/${l}` })),
  ]
}

export default function Home({ loaderData }: Route.ComponentProps) {
  const lang = useLang()
  const navigate = useNavigate()
  const [locating, setLocating] = useState(false)
  const [geoError, setGeoError] = useState(false)

  function nearMe() {
    if (!navigator.geolocation) return setGeoError(true)
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        const { latitude, longitude } = pos.coords
        navigate(`/${lang}/passeios?lat=${latitude.toFixed(5)}&lng=${longitude.toFixed(5)}&radius_km=15&sort=distance&view=map`)
      },
      () => {
        setLocating(false)
        setGeoError(true)
      },
      { timeout: 8000 },
    )
  }

  return (
    <>
      <section className="bg-gradient-to-br from-sky-700 via-sky-600 to-cyan-500 text-white">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:py-20">
          <h1 className="max-w-2xl text-3xl font-bold leading-tight sm:text-5xl">{t(lang, 'home.title')}</h1>
          <p className="mt-3 max-w-xl text-white/90 sm:text-lg">{t(lang, 'home.subtitle')}</p>
          <Form method="get" action={`/${lang}/passeios`} className="mt-8 flex max-w-2xl flex-col gap-2 sm:flex-row">
            <label htmlFor="q" className="sr-only">{t(lang, 'home.search')}</label>
            <input id="q" name="q" placeholder={t(lang, 'home.search')} className={`${inputClass} h-11 flex-1 bg-white text-foreground`} />
            <Button type="submit" size="lg" className="h-11 bg-white text-sky-700 hover:bg-white/90"><Search /> {t(lang, 'search.apply')}</Button>
            <Button type="button" size="lg" variant="outline" onClick={nearMe} disabled={locating}
              className="h-11 border-white/60 bg-transparent text-white hover:bg-white/10">
              <LocateFixed /> {locating ? t(lang, 'search.locating') : t(lang, 'home.near')}
            </Button>
          </Form>
          {geoError && <p className="mt-2 text-sm text-white/90">{t(lang, 'search.geoDenied')}</p>}
        </div>
      </section>

      <div className="mx-auto max-w-6xl space-y-12 px-4 py-10">
        <section>
          <h2 className="mb-4 text-xl font-semibold">{t(lang, 'home.categories')}</h2>
          <div className="flex flex-wrap gap-2">
            {loaderData.categories.map((c) => (
              <Link key={c.id} to={`/${lang}/passeios?category=${c.slug}`} prefetch="intent"
                className="rounded-full border bg-card px-4 py-2 text-sm hover:border-primary hover:text-primary">
                {c.name}
              </Link>
            ))}
          </div>
        </section>

        {loaderData.today.length > 0 && (
          <section>
            <div className="mb-4 flex items-end justify-between">
              <h2 className="text-xl font-semibold">{t(lang, 'home.today')}</h2>
              <Link to={`/${lang}/passeios?available=true&date=${todayRio()}`} className="text-sm text-primary hover:underline">{t(lang, 'home.all')}</Link>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {loaderData.today.map((tour) => <TourCard key={tour.id} tour={tour} lang={lang} />)}
            </div>
          </section>
        )}

        <section>
          <div className="mb-4 flex items-end justify-between">
            <h2 className="text-xl font-semibold">{t(lang, 'home.featured')}</h2>
            <Link to={`/${lang}/passeios`} className="text-sm text-primary hover:underline">{t(lang, 'home.all')}</Link>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {loaderData.featured.map((tour) => <TourCard key={tour.id} tour={tour} lang={lang} />)}
          </div>
        </section>
      </div>
    </>
  )
}

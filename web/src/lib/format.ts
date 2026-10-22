import type { Lang } from './types'

const TZ = 'America/Sao_Paulo'
const LOCALE: Record<Lang, string> = { pt: 'pt-BR', es: 'es', en: 'en-US' }

export function money(cents: number | null | undefined, lang: Lang = 'pt'): string {
  if (cents === null || cents === undefined) return '—'
  return new Intl.NumberFormat(LOCALE[lang], { style: 'currency', currency: 'BRL', currencyDisplay: 'narrowSymbol' }).format(cents / 100)
}

export function dateTime(iso: string | null | undefined, lang: Lang = 'pt'): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat(LOCALE[lang], {
    timeZone: TZ, weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso))
}

export function dateOnly(iso: string | null | undefined, lang: Lang = 'pt'): string {
  if (!iso) return '—'
  const d = iso.length === 10 ? new Date(`${iso}T12:00:00-03:00`) : new Date(iso)
  return new Intl.DateTimeFormat(LOCALE[lang], { timeZone: TZ, weekday: 'short', day: '2-digit', month: 'short' }).format(d)
}

export function duration(minutes: number, lang: Lang = 'pt'): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  const hl = lang === 'en' ? 'h' : 'h'
  if (h === 0) return `${m} min`
  return m ? `${h}${hl}${String(m).padStart(2, '0')}` : `${h}${hl}`
}

export function distance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined) return ''
  return meters < 1000 ? `${meters} m` : `${(meters / 1000).toFixed(1)} km`
}

/** "YYYY-MM-DD" de hoje no fuso do Rio. */
export function todayRio(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date())
}

export function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function reaisToCents(v: string): number {
  const n = Number(v.replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(n) ? Math.round(n * 100) : 0
}

export function centsToReais(c: number | null | undefined): string {
  if (c === null || c === undefined) return ''
  return (c / 100).toFixed(2).replace('.', ',')
}

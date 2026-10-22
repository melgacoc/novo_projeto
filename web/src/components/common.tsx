import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { AlertTriangle, Clock, ImageOff, Loader2, MapPin, Minus, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { distance, duration, money, dateTime } from '@/lib/format'
import { t } from '@/lib/i18n'
import type { Lang, TourCard as TourCardT } from '@/lib/types'
import { cn } from '@/lib/utils'

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Loading({ label = 'Carregando…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-10 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> {label}
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof ApiError ? error.message : 'Algo deu errado.'
  return (
    <div role="alert" className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <AlertTriangle className="size-4 text-destructive" /> {msg}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">{children}</div>
}

const STATUS_STYLE: Record<string, string> = {
  confirmed: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  completed: 'bg-sky-100 text-sky-800 border-sky-200',
  held: 'bg-amber-100 text-amber-800 border-amber-200',
  awaiting_operator: 'bg-amber-100 text-amber-800 border-amber-200',
  cancelled: 'bg-rose-100 text-rose-800 border-rose-200',
  expired: 'bg-slate-100 text-slate-600 border-slate-200',
  no_show: 'bg-orange-100 text-orange-800 border-orange-200',
  published: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  active: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  open: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  pending_review: 'bg-amber-100 text-amber-800 border-amber-200',
  pending: 'bg-amber-100 text-amber-800 border-amber-200',
  draft: 'bg-slate-100 text-slate-700 border-slate-200',
  invited: 'bg-slate-100 text-slate-700 border-slate-200',
  paused: 'bg-slate-200 text-slate-700 border-slate-300',
  closed: 'bg-slate-200 text-slate-700 border-slate-300',
  rejected: 'bg-rose-100 text-rose-800 border-rose-200',
  suspended: 'bg-rose-100 text-rose-800 border-rose-200',
  paid: 'bg-emerald-100 text-emerald-800 border-emerald-200',
}

const STATUS_PT: Record<string, string> = {
  held: 'Aguardando pagamento', awaiting_operator: 'Aguardando operadora', confirmed: 'Confirmada', expired: 'Expirada',
  cancelled: 'Cancelada', no_show: 'Não compareceu', completed: 'Realizada', published: 'Publicado',
  pending_review: 'Em análise', draft: 'Rascunho', paused: 'Pausado', rejected: 'Rejeitado', active: 'Ativa',
  invited: 'Convidada', suspended: 'Suspensa', open: 'Aberta', closed: 'Fechada', pending: 'Pendente', paid: 'Pago',
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return (
    <Badge variant="outline" className={cn('font-medium', STATUS_STYLE[status])}>
      {label ?? STATUS_PT[status] ?? status}
    </Badge>
  )
}

export function Photo({ src, alt, className }: { src: string | null | undefined; alt: string; className?: string }) {
  if (!src) {
    return (
      <div className={cn('flex items-center justify-center bg-gradient-to-br from-sky-500 to-cyan-400 text-white', className)}>
        <ImageOff className="size-6 opacity-70" />
      </div>
    )
  }
  return <img src={src} alt={alt} loading="lazy" className={cn('object-cover', className)} />
}

export function TourCard({ tour, lang }: { tour: TourCardT; lang: Lang }) {
  return (
    <Link
      to={`/${lang}/passeios/${tour.slug}`}
      prefetch="intent"
      className="group flex flex-col overflow-hidden rounded-xl border bg-card shadow-sm transition hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Photo src={tour.photo} alt={tour.title} className="aspect-[3/2] w-full transition group-hover:scale-[1.02]" />
      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {tour.category && <span>{tour.category.name}</span>}
          <span aria-hidden>·</span>
          <span className="flex items-center gap-1"><Clock className="size-3" />{duration(tour.duration_minutes, lang)}</span>
        </div>
        <h3 className="line-clamp-2 font-semibold leading-snug">{tour.title}</h3>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="size-3" /> {tour.area}
          {tour.distance_m !== null && <span>· {distance(tour.distance_m)}</span>}
        </p>
        <div className="mt-auto flex items-end justify-between pt-2">
          <div className="text-xs text-muted-foreground">
            {tour.next_departure ? <>{t(lang, 'card.next')}: {dateTime(tour.next_departure, lang)}</> : null}
          </div>
          <div className="text-right">
            <div className="text-[11px] text-muted-foreground">{t(lang, 'card.from')}</div>
            <div className="font-semibold text-primary">{money(tour.from_price_cents, lang)}</div>
          </div>
        </div>
      </div>
    </Link>
  )
}

export function Counter({ value, onChange, min = 0, max = 50, label }: { value: number; onChange: (v: number) => void; min?: number; max?: number; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <Button type="button" variant="outline" size="icon" aria-label={`- ${label}`} disabled={value <= min} onClick={() => onChange(value - 1)}>
        <Minus />
      </Button>
      <span className="w-6 text-center tabular-nums" aria-live="polite">{value}</span>
      <Button type="button" variant="outline" size="icon" aria-label={`+ ${label}`} disabled={value >= max} onClick={() => onChange(value + 1)}>
        <Plus />
      </Button>
    </div>
  )
}

export function Field({ label, children, hint, htmlFor }: { label: string; children: ReactNode; hint?: ReactNode; htmlFor?: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

export const inputClass =
  'h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50'

export const textareaClass =
  'min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring'

import { Suspense, lazy, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ImagePlus, Plus, Save, Search, Send, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorState, Field, StatusBadge, inputClass, textareaClass } from '@/components/common'
import { errorMessage, problemLabel } from '@/lib/messages'
import { api } from '@/lib/api'
import { centsToReais, reaisToCents, todayRio } from '@/lib/format'
import type { Category, Lang, PriceCategoryFull, Schedule, TourFull, Translation } from '@/lib/types'
import { cn } from '@/lib/utils'

const MapView = lazy(() => import('@/components/MapView').then((m) => ({ default: m.MapView })))

const LANG_LABEL: Record<Lang, string> = { pt: 'Português', es: 'Español', en: 'English' }
const WEEKDAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const CAT_DEFAULTS: Record<PriceCategoryFull['code'], Omit<PriceCategoryFull, 'prices'>> = {
  adult: { code: 'adult', min_age: 11, max_age: 120, label_pt: 'Adulto', label_es: 'Adulto', label_en: 'Adult' },
  child: { code: 'child', min_age: 3, max_age: 10, label_pt: 'Criança', label_es: 'Niño', label_en: 'Child' },
  infant: { code: 'infant', min_age: 0, max_age: 2, label_pt: 'Criança de colo', label_es: 'Bebé', label_en: 'Infant' },
  senior: { code: 'senior', min_age: 60, max_age: 120, label_pt: 'Idoso', label_es: 'Adulto mayor', label_en: 'Senior' },
}

type FormState = {
  category_id: number | null
  duration_minutes: number
  min_pax_per_booking: number
  max_pax_per_booking: number
  public_area_label: string
  meeting_point_address: string
  meeting_lat: number | null
  meeting_lng: number | null
  booking_cutoff_minutes: number
  cancellation_policy: 'flexible' | 'moderate' | 'strict'
  on_site_fees_note: string
  translations: Translation[]
  price_categories: (PriceCategoryFull & { pricesText: { price: string; valid_from: string; valid_to: string }[] })[]
}

function emptyTranslation(locale: Lang): Translation {
  return { locale, title: '', summary: '', description: '', includes: '', excludes: '', what_to_bring: '', meeting_point_details: '' }
}

function toForm(t?: TourFull): FormState {
  return {
    category_id: t?.category_id ?? null,
    duration_minutes: t?.duration_minutes ?? 240,
    min_pax_per_booking: t?.min_pax_per_booking ?? 1,
    max_pax_per_booking: t?.max_pax_per_booking ?? 10,
    public_area_label: t?.public_area_label ?? '',
    meeting_point_address: t?.meeting_point_address ?? '',
    meeting_lat: t?.meeting_lat ?? null,
    meeting_lng: t?.meeting_lng ?? null,
    booking_cutoff_minutes: t?.booking_cutoff_minutes ?? 120,
    cancellation_policy: t?.cancellation_policy ?? 'flexible',
    on_site_fees_note: t?.on_site_fees_note ?? '',
    translations: (['pt', 'es', 'en'] as Lang[]).map((l) => t?.translations.find((x) => x.locale === l) ?? emptyTranslation(l)),
    price_categories: (t?.price_categories.length ? t.price_categories : [{ ...CAT_DEFAULTS.adult, prices: [] }]).map((c) => ({
      ...c,
      pricesText: c.prices.length
        ? c.prices.map((p) => ({ price: centsToReais(p.price_cents), valid_from: p.valid_from, valid_to: p.valid_to ?? '' }))
        : [{ price: '', valid_from: todayRio(), valid_to: '' }],
    })),
  }
}

function toPayload(f: FormState) {
  return {
    ...f,
    price_categories: f.price_categories.map(({ pricesText, ...c }) => ({
      ...c,
      prices: pricesText
        .filter((p) => p.price !== '')
        .map((p) => ({ price_cents: reaisToCents(p.price), valid_from: p.valid_from, valid_to: p.valid_to || null })),
    })),
  }
}

type Props = {
  tour?: TourFull
  mode: 'operator' | 'admin'
  /** Para criar pelo admin (concierge). */
  operatorId?: number
  onSaved?: (t: TourFull) => void
}

export function TourEditor({ tour, mode, operatorId, onSaved }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState<FormState>(() => toForm(tour))
  const [tab, setTab] = useState<Lang>('pt')
  const [savedAt, setSavedAt] = useState<number | null>(null)
  const categories = useQuery({ queryKey: ['categories'], queryFn: () => api<Category[]>('/categories?locale=pt') })
  const opHeaders = tour ? { 'X-Operator-Id': String(tour.operator_id) } : operatorId ? { 'X-Operator-Id': String(operatorId) } : undefined

  const save = useMutation({
    mutationFn: () => {
      const body = toPayload(form)
      if (tour) {
        const path = mode === 'admin' ? `/admin/tours/${tour.id}` : `/operator/tours/${tour.id}`
        return api<TourFull>(path, { method: 'PUT', body })
      }
      if (mode === 'admin') return api<TourFull>(`/admin/operators/${operatorId}/tours`, { method: 'POST', body })
      return api<TourFull>('/operator/tours', { method: 'POST', body })
    },
    onSuccess: (t) => {
      setSavedAt(Date.now())
      qc.invalidateQueries({ queryKey: ['tour', t.id] })
      onSaved?.(t)
    },
  })

  const submit = useMutation({
    mutationFn: () => api<TourFull>(`/operator/tours/${tour!.id}/submit`, { method: 'POST', headers: opHeaders }),
    onSuccess: (t) => onSaved?.(t),
  })

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }))
  const setTr = (k: keyof Translation, v: string) =>
    setForm((f) => ({ ...f, translations: f.translations.map((t) => (t.locale === tab ? { ...t, [k]: v } : t)) }))
  const tr = form.translations.find((t) => t.locale === tab)!

  return (
    <div className="space-y-6">
      {tour && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-4">
          <StatusBadge status={tour.status} />
          {tour.review_notes && <span className="text-sm text-muted-foreground">Nota da análise: {tour.review_notes}</span>}
          {!!tour.problems?.length && (
            <span className="flex items-center gap-1 text-sm text-amber-700">
              <AlertTriangle className="size-4" /> Falta para publicar: {tour.problems.map(problemLabel).join(', ')}
            </span>
          )}
          {mode === 'operator' && ['draft', 'rejected', 'paused'].includes(tour.status) && (
            <Button className="ml-auto" disabled={submit.isPending} onClick={() => submit.mutate()}><Send /> Enviar para análise</Button>
          )}
          {submit.error && <p className="w-full text-sm text-destructive">{errorMessage(submit.error)}</p>}
        </div>
      )}
      {!!tour?.contact_flags?.length && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">
          <p className="mb-1 flex items-center gap-1 font-semibold"><AlertTriangle className="size-4" /> Possíveis dados de contato nos textos públicos</p>
          <p className="mb-2 text-amber-900">Contatos só podem aparecer no voucher (depois da reserva). Revise:</p>
          <ul className="list-disc pl-5">{tour.contact_flags.map((f, i) => <li key={i}><code>{f.field}</code>: “{f.match}”</li>)}</ul>
        </div>
      )}

      <form className="space-y-6" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <section className="space-y-4 rounded-xl border bg-card p-5">
          <h2 className="font-semibold">Informações básicas</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Categoria" htmlFor="cat">
              <select id="cat" className={inputClass} value={form.category_id ?? ''} onChange={(e) => set('category_id', e.target.value ? Number(e.target.value) : null)}>
                <option value="">Selecione…</option>
                {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name_pt}</option>)}
              </select>
            </Field>
            <Field label="Duração (minutos)" htmlFor="dur">
              <input id="dur" type="number" min={15} className={inputClass} value={form.duration_minutes} onChange={(e) => set('duration_minutes', Number(e.target.value))} />
            </Field>
            <Field label="Política de cancelamento" htmlFor="pol">
              <select id="pol" className={inputClass} value={form.cancellation_policy} onChange={(e) => set('cancellation_policy', e.target.value as FormState['cancellation_policy'])}>
                <option value="flexible">Flexível (integral até 24 h antes)</option>
                <option value="moderate">Moderada (integral até 48 h antes)</option>
                <option value="strict">Rígida (sem reembolso)</option>
              </select>
            </Field>
            <Field label="Pessoas por reserva (mín.)" htmlFor="pmin">
              <input id="pmin" type="number" min={1} className={inputClass} value={form.min_pax_per_booking} onChange={(e) => set('min_pax_per_booking', Number(e.target.value))} />
            </Field>
            <Field label="Pessoas por reserva (máx.)" htmlFor="pmax">
              <input id="pmax" type="number" min={1} className={inputClass} value={form.max_pax_per_booking} onChange={(e) => set('max_pax_per_booking', Number(e.target.value))} />
            </Field>
            <Field label="Fechar vendas antes da saída (horas)" htmlFor="cut" hint="Ex.: 12 para passeios que saem cedo de outra cidade">
              <input id="cut" type="number" min={0} step="0.5" className={inputClass} value={form.booking_cutoff_minutes / 60}
                onChange={(e) => set('booking_cutoff_minutes', Math.round(Number(e.target.value) * 60))} />
            </Field>
          </div>
          <Field label="Taxas pagas no local (opcional)" htmlFor="fees" hint="Ex.: taxa de embarque em Arraial do Cabo (~R$ 35 por pessoa)">
            <input id="fees" className={inputClass} value={form.on_site_fees_note} onChange={(e) => set('on_site_fees_note', e.target.value)} />
          </Field>
        </section>

        <LocationSection form={form} set={set} />

        <section className="space-y-4 rounded-xl border bg-card p-5">
          <h2 className="font-semibold">Textos (3 idiomas)</h2>
          <div className="flex gap-1 border-b" role="tablist">
            {(['pt', 'es', 'en'] as Lang[]).map((l) => {
              const filled = !!form.translations.find((t) => t.locale === l)?.title
              return (
                <button key={l} type="button" role="tab" aria-selected={tab === l} onClick={() => setTab(l)}
                  className={cn('-mb-px border-b-2 px-3 py-2 text-sm', tab === l ? 'border-primary font-semibold text-primary' : 'border-transparent text-muted-foreground')}>
                  {LANG_LABEL[l]} {filled ? '✓' : ''}
                </button>
              )
            })}
          </div>
          <div className="grid gap-4">
            <Field label="Título" htmlFor="t-title"><input id="t-title" className={inputClass} maxLength={160} value={tr.title} onChange={(e) => setTr('title', e.target.value)} /></Field>
            <Field label="Resumo (aparece nos cartões)" htmlFor="t-sum"><input id="t-sum" className={inputClass} maxLength={300} value={tr.summary} onChange={(e) => setTr('summary', e.target.value)} /></Field>
            <Field label="Descrição" htmlFor="t-desc"><textarea id="t-desc" className={cn(textareaClass, 'min-h-32')} value={tr.description} onChange={(e) => setTr('description', e.target.value)} /></Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Inclui (um item por linha)" htmlFor="t-inc"><textarea id="t-inc" className={textareaClass} value={tr.includes} onChange={(e) => setTr('includes', e.target.value)} /></Field>
              <Field label="Não inclui (um item por linha)" htmlFor="t-exc"><textarea id="t-exc" className={textareaClass} value={tr.excludes} onChange={(e) => setTr('excludes', e.target.value)} /></Field>
            </div>
            <Field label="O que levar" htmlFor="t-bring"><input id="t-bring" className={inputClass} value={tr.what_to_bring} onChange={(e) => setTr('what_to_bring', e.target.value)} /></Field>
            <Field label="Instruções do ponto de encontro (privado: só no voucher)" htmlFor="t-meet">
              <textarea id="t-meet" className={textareaClass} value={tr.meeting_point_details} onChange={(e) => setTr('meeting_point_details', e.target.value)} />
            </Field>
          </div>
        </section>

        <PricesSection form={form} setForm={setForm} />

        {save.error && <p className="text-sm text-destructive">{errorMessage(save.error)}</p>}
        <div className="sticky bottom-0 z-10 -mx-1 flex items-center gap-3 border-t bg-background/95 px-1 py-3 backdrop-blur">
          <Button type="submit" disabled={save.isPending}><Save /> {tour ? 'Salvar alterações' : 'Criar passeio'}</Button>
          {savedAt && !save.isPending && <span className="text-sm text-emerald-700">Salvo.</span>}
          {!tour && <span className="text-sm text-muted-foreground">Depois de criar, você adiciona fotos e agenda.</span>}
        </div>
      </form>

      {tour && <PhotosSection tour={tour} headers={opHeaders} />}
      {tour && <SchedulesSection tour={tour} headers={opHeaders} />}
    </div>
  )
}

function LocationSection({ form, set }: { form: FormState; set: <K extends keyof FormState>(k: K, v: FormState[K]) => void }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<{ label: string; lat: number; lng: number }[]>([])
  const [searching, setSearching] = useState(false)
  async function search() {
    if (q.trim().length < 3) return
    setSearching(true)
    try {
      setResults(await api(`/geocode?q=${encodeURIComponent(q)}`))
    } finally {
      setSearching(false)
    }
  }
  const point = form.meeting_lat !== null && form.meeting_lng !== null ? { lat: form.meeting_lat, lng: form.meeting_lng } : null
  const points = useMemo(() => (point ? [{ id: 'mp', lat: point.lat, lng: point.lng, label: '📍' }] : []), [point?.lat, point?.lng]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 className="font-semibold">Ponto de encontro</h2>
        <p className="text-sm text-muted-foreground">O turista vê só a região aproximada (~1 km). O endereço exato vai no voucher depois da reserva.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Endereço exato (privado)" htmlFor="addr">
          <input id="addr" className={inputClass} value={form.meeting_point_address} onChange={(e) => set('meeting_point_address', e.target.value)} />
        </Field>
        <Field label="Região exibida ao turista" htmlFor="area" hint="Ex.: Copacabana, Urca, São Conrado">
          <input id="area" className={inputClass} value={form.public_area_label} onChange={(e) => set('public_area_label', e.target.value)} />
        </Field>
      </div>
      <div className="flex gap-2">
        <input aria-label="Buscar endereço no mapa" placeholder="Buscar endereço no mapa…" className={inputClass} value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); search() } }} />
        <Button type="button" variant="outline" onClick={search} disabled={searching}><Search /> Buscar</Button>
      </div>
      {results.length > 0 && (
        <ul className="rounded-md border text-sm">
          {results.map((r, i) => (
            <li key={i}><button type="button" className="w-full px-3 py-2 text-left hover:bg-accent" onClick={() => {
              set('meeting_lat', Number(r.lat.toFixed(6)))
              set('meeting_lng', Number(r.lng.toFixed(6)))
              if (!form.meeting_point_address) set('meeting_point_address', r.label)
              setResults([])
            }}>{r.label}</button></li>
          ))}
        </ul>
      )}
      <Suspense fallback={<div className="h-72 rounded-lg bg-muted" />}>
        <MapView className="h-72 w-full rounded-lg border" points={points} center={point} zoom={point ? 14 : 11}
          onPick={(lat, lng) => { set('meeting_lat', Number(lat.toFixed(6))); set('meeting_lng', Number(lng.toFixed(6))) }} />
      </Suspense>
      <p className="text-xs text-muted-foreground">Clique no mapa para marcar o ponto exato. {point ? `(${point.lat}, ${point.lng})` : 'Nenhum ponto marcado.'}</p>
    </section>
  )
}

function PricesSection({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  const used = new Set(form.price_categories.map((c) => c.code))
  const update = (i: number, patch: Partial<FormState['price_categories'][number]>) =>
    setForm((f) => ({ ...f, price_categories: f.price_categories.map((c, j) => (j === i ? { ...c, ...patch } : c)) }))
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 className="font-semibold">Preços por faixa etária e temporada</h2>
        <p className="text-sm text-muted-foreground">Cada faixa pode ter vários períodos de preço (ex.: baixa e alta temporada). Os períodos não podem se sobrepor. Preço 0 = grátis.</p>
      </div>
      {form.price_categories.map((c, i) => (
        <div key={c.code} className="space-y-3 rounded-lg border p-4">
          <div className="flex flex-wrap items-end gap-3">
            <strong className="mr-auto">{c.label_pt || c.code}</strong>
            <Field label="Idade mín." htmlFor={`min-${c.code}`}><input id={`min-${c.code}`} type="number" min={0} className={cn(inputClass, 'w-24')} value={c.min_age} onChange={(e) => update(i, { min_age: Number(e.target.value) })} /></Field>
            <Field label="Idade máx." htmlFor={`max-${c.code}`}><input id={`max-${c.code}`} type="number" min={0} className={cn(inputClass, 'w-24')} value={c.max_age} onChange={(e) => update(i, { max_age: Number(e.target.value) })} /></Field>
            {c.code !== 'adult' && (
              <Button type="button" variant="ghost" size="icon" aria-label="Remover faixa"
                onClick={() => setForm((f) => ({ ...f, price_categories: f.price_categories.filter((_, j) => j !== i) }))}><Trash2 /></Button>
            )}
          </div>
          {c.pricesText.map((p, k) => (
            <div key={k} className="flex flex-wrap items-end gap-2">
              <Field label="Preço (R$)" htmlFor={`p-${c.code}-${k}`}>
                <input id={`p-${c.code}-${k}`} inputMode="decimal" placeholder="0,00" className={cn(inputClass, 'w-32')} value={p.price}
                  onChange={(e) => update(i, { pricesText: c.pricesText.map((x, z) => (z === k ? { ...x, price: e.target.value } : x)) })} />
              </Field>
              <Field label="De" htmlFor={`f-${c.code}-${k}`}>
                <input id={`f-${c.code}-${k}`} type="date" className={cn(inputClass, 'w-40')} value={p.valid_from}
                  onChange={(e) => update(i, { pricesText: c.pricesText.map((x, z) => (z === k ? { ...x, valid_from: e.target.value } : x)) })} />
              </Field>
              <Field label="Até (vazio = sem fim)" htmlFor={`t-${c.code}-${k}`}>
                <input id={`t-${c.code}-${k}`} type="date" className={cn(inputClass, 'w-40')} value={p.valid_to}
                  onChange={(e) => update(i, { pricesText: c.pricesText.map((x, z) => (z === k ? { ...x, valid_to: e.target.value } : x)) })} />
              </Field>
              {c.pricesText.length > 1 && (
                <Button type="button" variant="ghost" size="icon" aria-label="Remover período"
                  onClick={() => update(i, { pricesText: c.pricesText.filter((_, z) => z !== k) })}><Trash2 /></Button>
              )}
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={() => update(i, { pricesText: [...c.pricesText, { price: '', valid_from: todayRio(), valid_to: '' }] })}>
            <Plus /> Período de preço
          </Button>
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        {(['child', 'infant', 'senior'] as const).filter((code) => !used.has(code)).map((code) => (
          <Button key={code} type="button" variant="outline" size="sm"
            onClick={() => setForm((f) => ({ ...f, price_categories: [...f.price_categories, { ...CAT_DEFAULTS[code], prices: [], pricesText: [{ price: '', valid_from: todayRio(), valid_to: '' }] }] }))}>
            <Plus /> {CAT_DEFAULTS[code].label_pt}
          </Button>
        ))}
      </div>
    </section>
  )
}

function PhotosSection({ tour, headers }: { tour: TourFull; headers?: Record<string, string> }) {
  const qc = useQueryClient()
  const refresh = () => qc.invalidateQueries({ queryKey: ['tour', tour.id] })
  const upload = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('alt', tour.title)
      return api(`/operator/tours/${tour.id}/photos`, { method: 'POST', form: fd, headers })
    },
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api(`/operator/tours/${tour.id}/photos/${id}`, { method: 'DELETE', headers }),
    onSuccess: refresh,
  })
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 className="font-semibold">Fotos</h2>
        <p className="text-sm text-muted-foreground">JPG, PNG ou WebP até 5 MB. A primeira foto é a capa. Não use fotos com telefone, site ou @ da operadora.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tour.photos.map((p, i) => (
          <div key={p.id} className="group relative overflow-hidden rounded-lg border">
            <img src={p.url} alt={p.alt} className="aspect-[3/2] w-full object-cover" />
            {i === 0 && <span className="absolute left-2 top-2 rounded bg-black/60 px-1.5 text-xs text-white">Capa</span>}
            <button type="button" aria-label="Excluir foto" onClick={() => remove.mutate(p.id)}
              className="absolute right-2 top-2 rounded bg-white/90 p-1 text-destructive shadow"><Trash2 className="size-4" /></button>
          </div>
        ))}
        <label className="flex aspect-[3/2] cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed text-sm text-muted-foreground hover:border-primary">
          <ImagePlus className="size-6" /> {upload.isPending ? 'Enviando…' : 'Adicionar foto'}
          <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = '' }} />
        </label>
      </div>
      {upload.error && <ErrorState error={upload.error} />}
    </section>
  )
}

function SchedulesSection({ tour, headers }: { tour: TourFull; headers?: Record<string, string> }) {
  const qc = useQueryClient()
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6])
  const [time, setTime] = useState('08:00')
  const [capacity, setCapacity] = useState(20)
  const [validFrom, setValidFrom] = useState(todayRio())
  const [validTo, setValidTo] = useState('')
  const refresh = () => qc.invalidateQueries({ queryKey: ['tour', tour.id] })
  const create = useMutation({
    mutationFn: () => api<Schedule>(`/operator/tours/${tour.id}/schedules`, {
      method: 'POST', headers, body: { weekdays, start_time: time, capacity, valid_from: validFrom, valid_to: validTo || null },
    }),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api(`/operator/schedules/${id}`, { method: 'DELETE', headers }),
    onSuccess: refresh,
  })
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 className="font-semibold">Agenda (horários recorrentes)</h2>
        <p className="text-sm text-muted-foreground">As saídas dos próximos 90 dias são geradas automaticamente. Para exceções (fechar um dia, mudar vagas, saída extra), use a página Agenda.</p>
      </div>
      {tour.schedules.length > 0 && (
        <ul className="divide-y rounded-lg border text-sm">
          {tour.schedules.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
              <span className="font-medium">{s.start_time}</span>
              <span>{s.weekdays.map((d) => WEEKDAYS[d]).join(', ')}</span>
              <span className="text-muted-foreground">{s.capacity} vagas · desde {s.valid_from}{s.valid_to ? ` até ${s.valid_to}` : ''}</span>
              <Button type="button" variant="ghost" size="icon" className="ml-auto" aria-label="Remover horário" onClick={() => remove.mutate(s.id)}><Trash2 /></Button>
            </li>
          ))}
        </ul>
      )}
      <div className="space-y-3 rounded-lg border p-4">
        <div className="flex flex-wrap gap-1" role="group" aria-label="Dias da semana">
          {WEEKDAYS.map((d, i) => (
            <button key={d} type="button" aria-pressed={weekdays.includes(i)}
              onClick={() => setWeekdays((w) => (w.includes(i) ? w.filter((x) => x !== i) : [...w, i]))}
              className={cn('rounded-md border px-2.5 py-1 text-sm', weekdays.includes(i) ? 'border-primary bg-primary/10 text-primary' : 'text-muted-foreground')}>
              {d}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Horário" htmlFor="s-time"><input id="s-time" type="time" className={cn(inputClass, 'w-32')} value={time} onChange={(e) => setTime(e.target.value)} /></Field>
          <Field label="Vagas" htmlFor="s-cap"><input id="s-cap" type="number" min={1} className={cn(inputClass, 'w-24')} value={capacity} onChange={(e) => setCapacity(Number(e.target.value))} /></Field>
          <Field label="Desde" htmlFor="s-from"><input id="s-from" type="date" className={cn(inputClass, 'w-40')} value={validFrom} onChange={(e) => setValidFrom(e.target.value)} /></Field>
          <Field label="Até (opcional)" htmlFor="s-to"><input id="s-to" type="date" className={cn(inputClass, 'w-40')} value={validTo} onChange={(e) => setValidTo(e.target.value)} /></Field>
          <Button type="button" onClick={() => create.mutate()} disabled={create.isPending || weekdays.length === 0}><Plus /> Adicionar horário</Button>
        </div>
        {create.error && <p className="text-sm text-destructive">{errorMessage(create.error)}</p>}
      </div>
    </section>
  )
}

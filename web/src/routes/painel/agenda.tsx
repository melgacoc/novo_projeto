import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CloudRain, Lock, LockOpen, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Empty, ErrorState, Field, Loading, PageHeader, StatusBadge, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'
import { addDays, dateOnly, todayRio } from '@/lib/format'
import { useSession } from '@/lib/session-context'
import type { DepartureOperator } from '@/lib/types'
import { cn } from '@/lib/utils'

type TourRow = { id: number; title: string }

export default function Agenda() {
  const { operatorId } = useSession()
  const qc = useQueryClient()
  const [from, setFrom] = useState(todayRio())
  const [tourId, setTourId] = useState('')
  const to = addDays(from, 13)
  const tours = useQuery({ queryKey: ['op-tours', operatorId], queryFn: () => api<TourRow[]>('/operator/tours') })
  const deps = useQuery({
    queryKey: ['op-departures', operatorId, from, tourId],
    queryFn: () => api<DepartureOperator[]>(`/operator/departures?from=${from}&to=${to}${tourId ? `&tour_id=${tourId}` : ''}`),
  })
  const refresh = () => qc.invalidateQueries({ queryKey: ['op-departures'] })
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { capacity?: number; status?: string } }) =>
      api(`/operator/departures/${id}`, { method: 'PATCH', body }),
    onSuccess: refresh,
  })
  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      api<{ cancelled_bookings: number }>(`/operator/departures/${id}/cancel`, { method: 'POST', body: { reason } }),
    onSuccess: (r) => {
      refresh()
      window.alert(`Saída cancelada. ${r.cancelled_bookings} reserva(s) cancelada(s) com reembolso integral e aviso ao turista.`)
    },
  })

  const [extraTour, setExtraTour] = useState('')
  const [extraAt, setExtraAt] = useState(`${addDays(todayRio(), 1)}T09:00`)
  const [extraCap, setExtraCap] = useState(10)
  const extra = useMutation({
    mutationFn: () => api(`/operator/tours/${extraTour}/departures`, { method: 'POST', body: { starts_at_local: extraAt, capacity: extraCap } }),
    onSuccess: refresh,
  })

  const byDate = new Map<string, DepartureOperator[]>()
  for (const d of deps.data ?? []) byDate.set(d.date, [...(byDate.get(d.date) ?? []), d])

  return (
    <>
      <PageHeader title="Agenda" description="Saídas dos próximos 14 dias. Ajuste vagas, feche horários ou cancele por clima." />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="A partir de" htmlFor="ag-from"><input id="ag-from" type="date" className={cn(inputClass, 'w-44')} value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
        <Field label="Passeio" htmlFor="ag-tour">
          <select id="ag-tour" className={cn(inputClass, 'w-64')} value={tourId} onChange={(e) => setTourId(e.target.value)}>
            <option value="">Todos</option>
            {tours.data?.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
        </Field>
        <Button variant="outline" onClick={() => setFrom(addDays(from, -14))}>← Anteriores</Button>
        <Button variant="outline" onClick={() => setFrom(addDays(from, 14))}>Próximos →</Button>
      </div>
      {(patch.error || cancel.error) && <div className="mb-3"><ErrorState error={patch.error ?? cancel.error} /></div>}

      {deps.isLoading ? <Loading /> : deps.error ? <ErrorState error={deps.error} /> : byDate.size === 0 ? (
        <Empty>Nenhuma saída no período. Cadastre horários na página de cada passeio.</Empty>
      ) : (
        <div className="space-y-5">
          {[...byDate.entries()].map(([date, list]) => (
            <section key={date}>
              <h2 className="mb-2 text-sm font-semibold capitalize text-muted-foreground">{dateOnly(date)}</h2>
              <ul className="divide-y rounded-xl border bg-card">
                {list.map((d) => (
                  <li key={d.id} className="flex flex-wrap items-center gap-3 p-3 text-sm">
                    <span className="w-12 font-semibold tabular-nums">{d.time}</span>
                    <span className="min-w-40 flex-1">{d.title}</span>
                    <StatusBadge status={d.status} />
                    <span className="tabular-nums">{d.seats_booked} reservadas · {d.seats_held} em pagamento · {d.seats_available} livres</span>
                    {d.status !== 'cancelled' && (
                      <div className="flex flex-wrap items-center gap-1">
                        <label className="sr-only" htmlFor={`cap-${d.id}`}>Vagas</label>
                        <input id={`cap-${d.id}`} type="number" min={d.seats_booked + d.seats_held} defaultValue={d.capacity}
                          className={cn(inputClass, 'h-8 w-20')}
                          onBlur={(e) => Number(e.target.value) !== d.capacity && patch.mutate({ id: d.id, body: { capacity: Number(e.target.value) } })} />
                        {d.status === 'open' ? (
                          <Button size="sm" variant="ghost" title="Fechar vendas" onClick={() => patch.mutate({ id: d.id, body: { status: 'closed' } })}><Lock /> Fechar</Button>
                        ) : (
                          <Button size="sm" variant="ghost" title="Reabrir vendas" onClick={() => patch.mutate({ id: d.id, body: { status: 'open' } })}><LockOpen /> Abrir</Button>
                        )}
                        <Button size="sm" variant="ghost" className="text-destructive" onClick={() => {
                          if (window.confirm(`Cancelar esta saída por clima? ${d.seats_booked} pessoa(s) serão reembolsadas integralmente.`)) cancel.mutate({ id: d.id, reason: 'weather' })
                        }}><CloudRain /> Cancelar</Button>
                        {d.seats_booked > 0 && <Link className="text-primary underline" to={`/painel/reservas?departure_id=${d.id}`}>embarque</Link>}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <section className="mt-8 space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-semibold">Saída extra</h2>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Passeio" htmlFor="ex-tour">
            <select id="ex-tour" className={cn(inputClass, 'w-64')} value={extraTour} onChange={(e) => setExtraTour(e.target.value)}>
              <option value="">Selecione…</option>
              {tours.data?.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
          </Field>
          <Field label="Data e hora" htmlFor="ex-at"><input id="ex-at" type="datetime-local" className={cn(inputClass, 'w-56')} value={extraAt} onChange={(e) => setExtraAt(e.target.value)} /></Field>
          <Field label="Vagas" htmlFor="ex-cap"><input id="ex-cap" type="number" min={1} className={cn(inputClass, 'w-24')} value={extraCap} onChange={(e) => setExtraCap(Number(e.target.value))} /></Field>
          <Button disabled={!extraTour || extra.isPending} onClick={() => extra.mutate()}><Plus /> Criar saída</Button>
        </div>
        {extra.error && <p className="text-sm text-destructive">{errorMessage(extra.error)}</p>}
      </section>
    </>
  )
}

import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Empty, ErrorState, Field, Loading, PageHeader, StatusBadge, inputClass } from '@/components/common'
import { api } from '@/lib/api'
import { dateTime, money, todayRio } from '@/lib/format'
import { useSession } from '@/lib/session-context'
import type { Booking, Page } from '@/lib/types'
import { cn } from '@/lib/utils'

export default function PainelBookings() {
  const { operatorId } = useSession()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const departureId = params.get('departure_id')
  const [date, setDate] = useState(departureId ? '' : todayRio())
  const [status, setStatus] = useState('')
  const qs = new URLSearchParams({ page_size: '100' })
  if (date) qs.set('date', date)
  if (status) qs.set('status', status)
  if (departureId) qs.set('departure_id', departureId)
  const q = useQuery({ queryKey: ['op-bookings', operatorId, qs.toString()], queryFn: () => api<Page<Booking>>(`/operator/bookings?${qs}`) })
  const action = useMutation({
    mutationFn: ({ code, kind }: { code: string; kind: 'cancel' | 'no-show' }) => api(`/operator/bookings/${code}/${kind}`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['op-bookings'] }),
  })
  const items = q.data?.items ?? []
  const pax = items.filter((b) => ['confirmed', 'completed'].includes(b.status)).reduce((a, b) => a + b.pax_total, 0)

  return (
    <>
      <PageHeader title="Reservas" description="Lista de embarque por dia. O contato do turista aparece aqui só para reservas confirmadas." />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Data do passeio" htmlFor="b-date">
          <input id="b-date" type="date" className={cn(inputClass, 'w-44')} value={date} onChange={(e) => { setDate(e.target.value); setParams({}) }} />
        </Field>
        <Field label="Status" htmlFor="b-status">
          <select id="b-status" className={cn(inputClass, 'w-44')} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="confirmed">Confirmadas</option>
            <option value="completed">Realizadas</option>
            <option value="cancelled">Canceladas</option>
            <option value="no_show">Não compareceu</option>
          </select>
        </Field>
        {departureId && <Button variant="outline" onClick={() => { setParams({}); setDate(todayRio()) }}>Ver todas do dia</Button>}
        <span className="ml-auto text-sm text-muted-foreground">{items.length} reserva(s) · {pax} pessoa(s) confirmadas</span>
      </div>
      {action.error && <div className="mb-3"><ErrorState error={action.error} /></div>}
      {q.isLoading ? <Loading /> : q.error ? <ErrorState error={q.error} /> : items.length === 0 ? <Empty>Nenhuma reserva com esses filtros.</Empty> : (
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th className="p-3">Saída</th><th className="p-3">Passeio</th><th className="p-3">Titular</th><th className="p-3">Pessoas</th>
                <th className="p-3">Para você</th><th className="p-3">Status</th><th className="p-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((b) => (
                <tr key={b.code}>
                  <td className="p-3 capitalize">{dateTime(b.starts_at)}<div className="font-mono text-xs text-muted-foreground">{b.code}</div></td>
                  <td className="p-3">{b.title}</td>
                  <td className="p-3">{b.contact_name}
                    {b.contact_phone && <div><a className="text-xs text-primary underline" href={`https://wa.me/${b.contact_phone.replace(/\D/g, '')}`} target="_blank" rel="noreferrer">{b.contact_phone}</a></div>}
                  </td>
                  <td className="p-3">{b.items.map((i) => `${i.quantity}× ${i.label}`).join(', ')}</td>
                  <td className="p-3 tabular-nums">{money(b.operator_amount_cents)}</td>
                  <td className="p-3"><StatusBadge status={b.status} /></td>
                  <td className="p-3 text-right">
                    {b.status === 'confirmed' && (
                      <div className="flex justify-end gap-1">
                        {new Date(b.starts_at) <= new Date() && (
                          <Button size="sm" variant="outline" onClick={() => action.mutate({ code: b.code, kind: 'no-show' })}>No-show</Button>
                        )}
                        <Button size="sm" variant="ghost" className="text-destructive" onClick={() => {
                          if (window.confirm('Cancelar esta reserva? O turista recebe reembolso integral e o cancelamento conta no seu histórico.')) action.mutate({ code: b.code, kind: 'cancel' })
                        }}>Cancelar</Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

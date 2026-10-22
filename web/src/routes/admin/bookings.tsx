import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Empty, ErrorState, Field, Loading, PageHeader, StatusBadge, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'
import { centsToReais, dateTime, money, reaisToCents } from '@/lib/format'
import type { Booking, Page } from '@/lib/types'

type Detail = Booking & { refunds: { amount_cents: number; reason: string; status: string; created_at: string }[] }

export default function AdminBookings() {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const qs = new URLSearchParams({ page_size: '50' })
  if (q) qs.set('q', q)
  if (status) qs.set('status', status)
  const list = useQuery({ queryKey: ['admin-bookings', qs.toString()], queryFn: () => api<Page<Booking>>(`/admin/bookings?${qs}`) })
  const [code, setCode] = useState<string | null>(null)
  const detail = useQuery({ queryKey: ['admin-booking', code], queryFn: () => api<Detail>(`/admin/bookings/${code}`), enabled: !!code })
  const [refund, setRefund] = useState('')
  const cancel = useMutation({
    mutationFn: () => api<Detail>(`/admin/bookings/${code}/cancel`, { method: 'POST', body: { reason: 'admin', refund_cents: refund === '' ? null : reaisToCents(refund) } }),
    onSuccess: (d) => { qc.setQueryData(['admin-booking', code], d); qc.invalidateQueries({ queryKey: ['admin-bookings'] }) },
  })
  const b = detail.data
  return (
    <>
      <PageHeader title="Reservas" />
      <div className="mb-4 flex flex-wrap gap-2">
        <input aria-label="Buscar" placeholder="Código, nome ou e-mail" className={`${inputClass} max-w-xs`} value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label="Status" className={`${inputClass} max-w-48`} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Todos os status</option>
          {['held', 'confirmed', 'completed', 'cancelled', 'no_show'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {list.isLoading ? <Loading /> : list.error ? <ErrorState error={list.error} /> : !list.data?.items.length ? <Empty>Nenhuma reserva.</Empty> : (
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left"><tr><th className="p-3">Código</th><th className="p-3">Passeio</th><th className="p-3">Saída</th><th className="p-3">Turista</th><th className="p-3 text-right">Total</th><th className="p-3 text-right">Comissão</th><th className="p-3">Status</th></tr></thead>
            <tbody className="divide-y">
              {list.data.items.map((r) => (
                <tr key={r.code} className="cursor-pointer hover:bg-accent/50" onClick={() => { setCode(r.code); setRefund('') }}>
                  <td className="p-3 font-mono">{r.code}</td><td className="p-3">{r.title}<div className="text-xs text-muted-foreground">{r.operator_name}</div></td>
                  <td className="p-3 capitalize">{dateTime(r.starts_at)}</td><td className="p-3">{r.contact_name}<div className="text-xs text-muted-foreground">{r.contact_email}</div></td>
                  <td className="p-3 text-right tabular-nums">{money(r.total_cents)}</td><td className="p-3 text-right tabular-nums">{money(r.commission_cents)}</td>
                  <td className="p-3"><StatusBadge status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Dialog open={!!code} onOpenChange={(o) => !o && setCode(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Reserva {code}</DialogTitle></DialogHeader>
          {detail.isLoading || !b ? <Loading /> : (
            <div className="space-y-3 text-sm">
              <p><strong>{b.title}</strong> · {dateTime(b.starts_at)}</p>
              <p>{b.contact_name} · {b.contact_email} · {b.contact_phone}</p>
              <p>{b.items.map((i) => `${i.quantity}× ${i.label}`).join(', ')} · Total {money(b.total_cents)} · Comissão {money(b.commission_cents)} ({((b.commission_rate ?? 0) * 100).toFixed(1)}%)</p>
              <p>Status: <StatusBadge status={b.status} /> {b.cancel_reason && `(${b.cancel_reason})`}</p>
              <p>Pagamentos: {b.payments.map((p) => `${p.method} ${p.status} ${money(p.amount_cents)}`).join('; ') || '—'}</p>
              <p>Reembolsos: {b.refunds.map((r) => `${money(r.amount_cents)} (${r.reason})`).join('; ') || '—'}</p>
              {b.status === 'confirmed' && (
                <div className="space-y-2 rounded-md border p-3">
                  <Field label="Valor a reembolsar (R$)" htmlFor="ab-ref" hint={`Vazio = integral (${centsToReais(b.total_cents)})`}>
                    <input id="ab-ref" inputMode="decimal" className={inputClass} value={refund} onChange={(e) => setRefund(e.target.value)} />
                  </Field>
                  <Button variant="destructive" disabled={cancel.isPending} onClick={() => window.confirm('Cancelar esta reserva?') && cancel.mutate()}>Cancelar reserva</Button>
                  {cancel.error && <p className="text-destructive">{errorMessage(cancel.error)}</p>}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

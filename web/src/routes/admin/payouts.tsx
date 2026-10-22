import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Wallet } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Empty, ErrorState, Loading, PageHeader, StatusBadge } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'
import { dateOnly, money } from '@/lib/format'

type P = { id: number; operator_name: string; period_start: string; period_end: string; amount_cents: number; status: string; items_count: number; paid_at: string | null; transfer_id: string | null }
type Data = { items: P[]; eligible: { operator_id: number; operator_name: string; amount_cents: number }[]; payout_delay_days: number }

export default function AdminPayouts() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-payouts'], queryFn: () => api<Data>('/admin/payouts') })
  const refresh = () => qc.invalidateQueries({ queryKey: ['admin-payouts'] })
  const generate = useMutation({ mutationFn: () => api('/admin/payouts/generate', { method: 'POST' }), onSuccess: refresh })
  const paid = useMutation({
    mutationFn: (id: number) => api(`/admin/payouts/${id}/mark-paid`, { method: 'POST', body: { transfer_id: window.prompt('ID da transferência (opcional)') || null, notes: '' } }),
    onSuccess: refresh,
  })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const d = q.data
  return (
    <>
      <PageHeader title="Repasses às operadoras" description={`Valor da operadora liberado ${d.payout_delay_days} dia(s) depois do passeio realizado (ou no-show).`}
        actions={<Button disabled={!d.eligible.length || generate.isPending} onClick={() => generate.mutate()}><Wallet /> Gerar repasses</Button>} />
      {generate.error && <p className="mb-3 text-sm text-destructive">{errorMessage(generate.error)}</p>}
      <h2 className="mb-2 font-semibold">Liberado e ainda não agrupado</h2>
      {d.eligible.length === 0 ? <p className="mb-6 text-sm text-muted-foreground">Nada liberado no momento.</p> : (
        <ul className="mb-6 divide-y rounded-xl border bg-card text-sm">{d.eligible.map((e) => <li key={e.operator_id} className="flex justify-between p-3"><span>{e.operator_name}</span><span className="font-semibold tabular-nums">{money(e.amount_cents)}</span></li>)}</ul>
      )}
      <h2 className="mb-2 font-semibold">Repasses gerados</h2>
      {d.items.length === 0 ? <Empty>Nenhum repasse gerado ainda.</Empty> : (
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left"><tr><th className="p-3">Operadora</th><th className="p-3">Período</th><th className="p-3">Reservas</th><th className="p-3 text-right">Valor</th><th className="p-3">Status</th><th className="p-3"></th></tr></thead>
            <tbody className="divide-y">
              {d.items.map((p) => (
                <tr key={p.id}>
                  <td className="p-3">{p.operator_name}</td><td className="p-3">{dateOnly(p.period_start)} – {dateOnly(p.period_end)}</td><td className="p-3">{p.items_count}</td>
                  <td className="p-3 text-right font-semibold tabular-nums">{money(p.amount_cents)}</td><td className="p-3"><StatusBadge status={p.status} /></td>
                  <td className="p-3 text-right">{p.status === 'pending' ? <Button size="sm" variant="outline" onClick={() => paid.mutate(p.id)}>Marcar como pago</Button> : <span className="text-xs text-muted-foreground">{p.transfer_id}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

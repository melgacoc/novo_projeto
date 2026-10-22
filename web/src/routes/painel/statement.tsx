import { useQuery } from '@tanstack/react-query'
import { ErrorState, Loading, PageHeader, StatusBadge } from '@/components/common'
import { api } from '@/lib/api'
import { dateOnly, dateTime, money } from '@/lib/format'
import { useSession } from '@/lib/session-context'

type Statement = {
  items: { code: string; title: string; starts_at: string; status: string; pax_total: number; total_cents: number; commission_cents: number; operator_amount_cents: number }[]
  totals: { gross_cents: number; commission_cents: number; operator_amount_cents: number }
  pending_payout_cents: number
  upcoming_amount_cents: number
  payouts: { id: number; period_start: string; period_end: string; amount_cents: number; status: string; paid_at: string | null }[]
}

export default function PainelStatement() {
  const { operatorId } = useSession()
  const q = useQuery({ queryKey: ['op-statement', operatorId], queryFn: () => api<Statement>('/operator/statement') })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const d = q.data
  const cards = [
    { label: 'Vendido (período)', value: money(d.totals.gross_cents) },
    { label: 'Comissão da plataforma', value: money(d.totals.commission_cents) },
    { label: 'Valor da operadora', value: money(d.totals.operator_amount_cents) },
    { label: 'Liberado para repasse', value: money(d.pending_payout_cents) },
  ]
  return (
    <>
      <PageHeader title="Extrato" description="Últimos 30 dias e próximos 60. O valor é liberado para repasse depois que o passeio acontece." />
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl border bg-card p-4"><div className="text-sm text-muted-foreground">{c.label}</div><div className="mt-1 text-xl font-semibold tabular-nums">{c.value}</div></div>
        ))}
      </div>
      <h2 className="mb-2 font-semibold">Repasses</h2>
      {d.payouts.length === 0 ? <p className="mb-8 text-sm text-muted-foreground">Nenhum repasse gerado ainda.</p> : (
        <ul className="mb-8 divide-y rounded-xl border bg-card text-sm">
          {d.payouts.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
              <span>{dateOnly(p.period_start)} – {dateOnly(p.period_end)}</span>
              <span className="font-semibold tabular-nums">{money(p.amount_cents)}</span>
              <StatusBadge status={p.status} />
            </li>
          ))}
        </ul>
      )}
      <h2 className="mb-2 font-semibold">Reservas pagas</h2>
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50 text-left"><tr><th className="p-3">Saída</th><th className="p-3">Passeio</th><th className="p-3">Status</th><th className="p-3 text-right">Total</th><th className="p-3 text-right">Comissão</th><th className="p-3 text-right">Para você</th></tr></thead>
          <tbody className="divide-y">
            {d.items.map((i) => (
              <tr key={i.code}>
                <td className="p-3 capitalize">{dateTime(i.starts_at)}<div className="font-mono text-xs text-muted-foreground">{i.code}</div></td>
                <td className="p-3">{i.title}</td>
                <td className="p-3"><StatusBadge status={i.status} /></td>
                <td className="p-3 text-right tabular-nums">{money(i.total_cents)}</td>
                <td className="p-3 text-right tabular-nums">{money(i.commission_cents)}</td>
                <td className="p-3 text-right font-medium tabular-nums">{money(i.operator_amount_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

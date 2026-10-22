import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ErrorState, Loading, PageHeader } from '@/components/common'
import { api } from '@/lib/api'
import { money } from '@/lib/format'

type Window = { bookings: number; gmv_cents: number; commission_cents: number }
type Metrics = {
  last_7_days: Window
  last_30_days: Window
  funnel_7_days: { holds: number; paid: number; expired: number }
  refunds_30d_cents: number
  operators_by_status: Record<string, number>
  tours_by_status: Record<string, number>
  pending_review: number
  cancellations_by_operator: { operator: string; count: number }[]
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  )
}

export default function AdminDashboard() {
  const q = useQuery({ queryKey: ['admin-metrics'], queryFn: () => api<Metrics>('/admin/metrics'), refetchInterval: 60_000 })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const m = q.data
  const conv = m.funnel_7_days.holds ? Math.round((m.funnel_7_days.paid / m.funnel_7_days.holds) * 100) : 0
  return (
    <>
      <PageHeader title="Visão geral" />
      {m.pending_review > 0 && (
        <Link to="/admin/passeios" className="mb-6 block rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">
          <strong>{m.pending_review}</strong> passeio(s) aguardando análise →
        </Link>
      )}
      <h2 className="mb-2 text-sm font-semibold text-muted-foreground">Últimos 7 dias</h2>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Reservas pagas" value={String(m.last_7_days.bookings)} />
        <Kpi label="Vendido (GMV)" value={money(m.last_7_days.gmv_cents)} />
        <Kpi label="Comissão" value={money(m.last_7_days.commission_cents)} />
        <Kpi label="Conversão retenção → pagamento" value={`${conv}%`} hint={`${m.funnel_7_days.paid} pagas de ${m.funnel_7_days.holds} retenções · ${m.funnel_7_days.expired} expiradas`} />
      </div>
      <h2 className="mb-2 text-sm font-semibold text-muted-foreground">Últimos 30 dias</h2>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Reservas pagas" value={String(m.last_30_days.bookings)} />
        <Kpi label="Vendido (GMV)" value={money(m.last_30_days.gmv_cents)} />
        <Kpi label="Comissão" value={money(m.last_30_days.commission_cents)} />
        <Kpi label="Reembolsos" value={money(m.refunds_30d_cents)} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border bg-card p-4 text-sm"><h3 className="mb-2 font-semibold">Operadoras</h3>{Object.entries(m.operators_by_status).map(([k, v]) => <div key={k}>{k}: {v}</div>)}</div>
        <div className="rounded-xl border bg-card p-4 text-sm"><h3 className="mb-2 font-semibold">Passeios</h3>{Object.entries(m.tours_by_status).map(([k, v]) => <div key={k}>{k}: {v}</div>)}</div>
        <div className="rounded-xl border bg-card p-4 text-sm"><h3 className="mb-2 font-semibold">Cancelamentos por operadora</h3>
          {m.cancellations_by_operator.length ? m.cancellations_by_operator.map((c) => <div key={c.operator}>{c.operator}: {c.count}</div>) : <p className="text-muted-foreground">Nenhum.</p>}
        </div>
      </div>
      <p className="mt-6 text-xs text-muted-foreground">Funil detalhado do turista (visitas, buscas, checkout): conectar PostHog (ver docs/integracoes.md).</p>
    </>
  )
}

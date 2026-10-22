import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Empty, ErrorState, Loading, PageHeader } from '@/components/common'
import { api } from '@/lib/api'
import { dateTime, money } from '@/lib/format'
import { useSession } from '@/lib/session-context'
import type { DepartureOperator } from '@/lib/types'

type Dashboard = {
  operator: { id: number; public_name: string; status: string }
  upcoming: DepartureOperator[]
  tours_by_status: Record<string, number>
  month_bookings: number
  month_amount_cents: number
  pending_payout_cents: number
  upcoming_amount_cents: number
}

export default function PainelDashboard() {
  const { operatorId } = useSession()
  const q = useQuery({ queryKey: ['op-dashboard', operatorId], queryFn: () => api<Dashboard>('/operator/dashboard') })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const d = q.data
  const kpis = [
    { label: 'Reservas no mês', value: String(d.month_bookings) },
    { label: 'A receber no mês', value: money(d.month_amount_cents) },
    { label: 'Liberado para repasse', value: money(d.pending_payout_cents) },
    { label: 'Reservas futuras (a receber)', value: money(d.upcoming_amount_cents) },
  ]
  return (
    <>
      <PageHeader title={d.operator.public_name} description="Visão geral das próximas 48 horas e do mês." />
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-xl border bg-card p-4">
            <div className="text-sm text-muted-foreground">{k.label}</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">{k.value}</div>
          </div>
        ))}
      </div>
      <h2 className="mb-3 font-semibold">Próximas saídas com reservas</h2>
      {d.upcoming.length === 0 ? (
        <Empty>Nenhuma saída com reservas nas próximas 48 horas.</Empty>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {d.upcoming.map((dep) => (
            <li key={dep.id} className="flex flex-wrap items-center justify-between gap-2 p-4">
              <div>
                <div className="font-medium">{dep.title}</div>
                <div className="text-sm capitalize text-muted-foreground">{dateTime(dep.starts_at)}</div>
              </div>
              <div className="text-sm">{dep.seats_booked}/{dep.capacity} pessoas</div>
              <Link className="text-sm text-primary underline" to={`/painel/reservas?departure_id=${dep.id}`}>Lista de embarque</Link>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-6 text-sm text-muted-foreground">
        Passeios: {Object.entries(d.tours_by_status).map(([k, v]) => `${v} ${k}`).join(' · ') || 'nenhum'} · <Link className="text-primary underline" to="/painel/passeios">gerenciar</Link>
      </p>
    </>
  )
}

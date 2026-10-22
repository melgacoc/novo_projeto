import { Link, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { Empty, ErrorState, Loading, PageHeader, Photo, StatusBadge, inputClass } from '@/components/common'
import { problemLabel } from '@/lib/messages'
import { api } from '@/lib/api'
import { money } from '@/lib/format'
import type { Page } from '@/lib/types'

type Row = { id: number; slug: string; title: string; status: string; operator_name: string; from_price_cents: number | null; photo: string | null; problems: string[]; flags: unknown[] }
const STATUSES = [['pending_review', 'Em análise'], ['published', 'Publicados'], ['draft', 'Rascunhos'], ['paused', 'Pausados'], ['rejected', 'Rejeitados'], ['', 'Todos']]

export default function AdminTours() {
  const [params, setParams] = useSearchParams()
  const status = params.get('status') ?? 'pending_review'
  const operatorId = params.get('operator_id')
  const qs = new URLSearchParams({ page_size: '100' })
  if (status) qs.set('status', status)
  if (operatorId) qs.set('operator_id', operatorId)
  const q = useQuery({ queryKey: ['admin-tours', qs.toString()], queryFn: () => api<Page<Row>>(`/admin/tours?${qs}`) })
  return (
    <>
      <PageHeader title="Passeios" description="Fila de aprovação e todos os passeios da plataforma." />
      <div className="mb-4 flex flex-wrap gap-2">
        {STATUSES.map(([v, label]) => (
          <button key={v} type="button" onClick={() => { const n = new URLSearchParams(params); n.set('status', v); setParams(n) }}
            className={`rounded-full border px-3 py-1 text-sm ${status === v ? 'border-primary bg-primary/10 text-primary' : ''}`}>{label}</button>
        ))}
        {operatorId && <span className={`${inputClass} w-auto`}>Operadora #{operatorId}</span>}
      </div>
      {q.isLoading ? <Loading /> : q.error ? <ErrorState error={q.error} /> : !q.data?.items.length ? <Empty>Nada por aqui.</Empty> : (
        <ul className="divide-y rounded-xl border bg-card">
          {q.data.items.map((t) => (
            <li key={t.id}>
              <Link to={`/admin/passeios/${t.id}`} className="flex items-center gap-4 p-3 hover:bg-accent/50">
                <Photo src={t.photo} alt={t.title} className="h-14 w-20 shrink-0 rounded-md" />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{t.title || t.slug}</div>
                  <div className="text-xs text-muted-foreground">{t.operator_name} · {money(t.from_price_cents)}</div>
                  {t.problems.length > 0 && <div className="text-xs text-amber-700">Falta: {t.problems.map(problemLabel).join(', ')}</div>}
                </div>
                {t.flags.length > 0 && <span title="Possíveis contatos nos textos" className="text-amber-600"><AlertTriangle className="size-4" /></span>}
                <StatusBadge status={t.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

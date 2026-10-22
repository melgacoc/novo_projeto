import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Empty, ErrorState, Loading, PageHeader, Photo, StatusBadge } from '@/components/common'
import { problemLabel } from '@/lib/messages'
import { api } from '@/lib/api'
import { money } from '@/lib/format'
import { useSession } from '@/lib/session-context'

type Row = { id: number; slug: string; title: string; status: string; from_price_cents: number | null; photo: string | null; problems: string[] }

export default function PainelTours() {
  const { operatorId } = useSession()
  const q = useQuery({ queryKey: ['op-tours', operatorId], queryFn: () => api<Row[]>('/operator/tours') })
  return (
    <>
      <PageHeader title="Passeios" description="Cadastre, edite e envie seus passeios para análise."
        actions={<Button asChild><Link to="/painel/passeios/novo"><Plus /> Novo passeio</Link></Button>} />
      {q.isLoading ? <Loading /> : q.error ? <ErrorState error={q.error} /> : !q.data?.length ? (
        <Empty>Nenhum passeio ainda. Comece pelo botão “Novo passeio”.</Empty>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {q.data.map((t) => (
            <li key={t.id}>
              <Link to={`/painel/passeios/${t.id}`} className="block overflow-hidden rounded-xl border bg-card hover:border-primary">
                <Photo src={t.photo} alt={t.title} className="aspect-[3/2] w-full" />
                <div className="space-y-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-medium">{t.title || 'Sem título'}</span>
                    <StatusBadge status={t.status} />
                  </div>
                  <div className="text-sm text-muted-foreground">{money(t.from_price_cents)}</div>
                  {t.problems.length > 0 && <p className="text-xs text-amber-700">Falta: {t.problems.map(problemLabel).join(', ')}</p>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

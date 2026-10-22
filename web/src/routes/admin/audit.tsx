import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ErrorState, Loading, PageHeader, inputClass } from '@/components/common'
import { api } from '@/lib/api'
import { dateTime } from '@/lib/format'
import type { Page } from '@/lib/types'

type Log = { id: number; user: string | null; entity: string; entity_id: string; action: string; old: unknown; new: unknown; created_at: string }

export default function AdminAudit() {
  const [entity, setEntity] = useState('')
  const q = useQuery({ queryKey: ['admin-audit', entity], queryFn: () => api<Page<Log>>(`/admin/audit-logs?page_size=100${entity ? `&entity=${entity}` : ''}`) })
  return (
    <>
      <PageHeader title="Auditoria" description="Quem alterou o quê e quando." />
      <select aria-label="Entidade" className={`${inputClass} mb-4 max-w-48`} value={entity} onChange={(e) => setEntity(e.target.value)}>
        <option value="">Todas</option>{['operator', 'tour', 'booking', 'departure', 'payout', 'settings', 'user', 'payment'].map((e) => <option key={e} value={e}>{e}</option>)}
      </select>
      {q.isLoading ? <Loading /> : q.error ? <ErrorState error={q.error} /> : (
        <ul className="divide-y rounded-xl border bg-card text-sm">
          {q.data?.items.map((l) => (
            <li key={l.id} className="p-3">
              <div className="flex flex-wrap gap-2"><span className="text-muted-foreground">{dateTime(l.created_at)}</span><strong>{l.action}</strong><span>{l.entity} #{l.entity_id}</span><span className="text-muted-foreground">por {l.user ?? 'sistema'}</span></div>
              {(l.old || l.new) ? <pre className="mt-1 overflow-x-auto rounded bg-muted p-2 text-xs">{JSON.stringify({ antes: l.old, depois: l.new }, null, 0)}</pre> : null}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

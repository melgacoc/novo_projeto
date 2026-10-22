import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ErrorState, Loading, PageHeader, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'
import { dateOnly } from '@/lib/format'
import type { Page } from '@/lib/types'

type U = { id: number; email: string; name: string; role: string; is_active: boolean; is_dev_user: boolean; created_at: string }

export default function AdminUsers() {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const qs = new URLSearchParams({ page_size: '100' })
  if (q) qs.set('q', q)
  if (role) qs.set('role', role)
  const list = useQuery({ queryKey: ['admin-users', qs.toString()], queryFn: () => api<Page<U>>(`/admin/users?${qs}`) })
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<U> }) => api(`/admin/users/${id}`, { method: 'PATCH', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })
  return (
    <>
      <PageHeader title="Usuários" />
      <div className="mb-4 flex gap-2">
        <input aria-label="Buscar" placeholder="E-mail ou nome" className={`${inputClass} max-w-xs`} value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label="Papel" className={`${inputClass} max-w-40`} value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">Todos</option><option value="tourist">Turistas</option><option value="operator">Operadoras</option><option value="admin">Admins</option>
        </select>
      </div>
      {patch.error && <p className="mb-2 text-sm text-destructive">{errorMessage(patch.error)}</p>}
      {list.isLoading ? <Loading /> : list.error ? <ErrorState error={list.error} /> : (
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left"><tr><th className="p-3">Usuário</th><th className="p-3">Papel</th><th className="p-3">Ativo</th><th className="p-3">Desde</th></tr></thead>
            <tbody className="divide-y">
              {list.data?.items.map((u) => (
                <tr key={u.id}>
                  <td className="p-3">{u.name || '—'}<div className="text-xs text-muted-foreground">{u.email}{u.is_dev_user && ' · usuário de desenvolvimento'}</div></td>
                  <td className="p-3">
                    <select aria-label="Papel" className={`${inputClass} h-8 w-36`} value={u.role} onChange={(e) => patch.mutate({ id: u.id, body: { role: e.target.value } })}>
                      <option value="tourist">Turista</option><option value="operator">Operadora</option><option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="p-3"><input type="checkbox" aria-label="Ativo" checked={u.is_active} onChange={(e) => patch.mutate({ id: u.id, body: { is_active: e.target.checked } })} /></td>
                  <td className="p-3">{dateOnly(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

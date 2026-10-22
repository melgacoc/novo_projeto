import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorState, Loading, PageHeader, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'
import type { Category } from '@/lib/types'

const EMPTY = { slug: '', name_pt: '', name_es: '', name_en: '', icon: 'map-pin', position: 0 }

export default function AdminCategories() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-categories'], queryFn: () => api<Category[]>('/admin/categories') })
  const [form, setForm] = useState(EMPTY)
  const refresh = () => { qc.invalidateQueries({ queryKey: ['admin-categories'] }); qc.invalidateQueries({ queryKey: ['categories'] }) }
  const create = useMutation({ mutationFn: () => api('/admin/categories', { method: 'POST', body: form }), onSuccess: () => { setForm(EMPTY); refresh() } })
  const update = useMutation({ mutationFn: (c: Category) => api(`/admin/categories/${c.id}`, { method: 'PUT', body: c }), onSuccess: refresh })
  const remove = useMutation({ mutationFn: (id: number) => api(`/admin/categories/${id}`, { method: 'DELETE' }), onSuccess: refresh })
  if (q.isLoading) return <Loading />
  if (q.error) return <ErrorState error={q.error} />
  const cols: (keyof typeof EMPTY)[] = ['slug', 'name_pt', 'name_es', 'name_en', 'position']
  return (
    <>
      <PageHeader title="Categorias" description="Nomes nos 3 idiomas. Edite e saia do campo para salvar." />
      {(update.error || remove.error) && <p className="mb-3 text-sm text-destructive">{errorMessage(update.error ?? remove.error)}</p>}
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50 text-left"><tr>{cols.map((c) => <th key={c} className="p-2">{c}</th>)}<th /></tr></thead>
          <tbody className="divide-y">
            {q.data?.map((c) => (
              <tr key={c.id}>
                {cols.map((k) => (
                  <td key={k} className="p-2"><input aria-label={k} defaultValue={String(c[k as keyof Category] ?? '')} className={inputClass}
                    onBlur={(e) => { const v = k === 'position' ? Number(e.target.value) : e.target.value; if (v !== c[k as keyof Category]) update.mutate({ ...c, [k]: v }) }} /></td>
                ))}
                <td className="p-2"><Button size="icon" variant="ghost" aria-label="Excluir" onClick={() => window.confirm('Excluir categoria?') && remove.mutate(c.id)}><Trash2 /></Button></td>
              </tr>
            ))}
            <tr>
              {cols.map((k) => (
                <td key={k} className="p-2"><input aria-label={`nova ${k}`} placeholder={k} className={inputClass} value={String(form[k])}
                  onChange={(e) => setForm({ ...form, [k]: k === 'position' ? Number(e.target.value) : e.target.value })} /></td>
              ))}
              <td className="p-2"><Button size="sm" onClick={() => create.mutate()} disabled={!form.slug || !form.name_pt}>Adicionar</Button></td>
            </tr>
          </tbody>
        </table>
      </div>
      {create.error && <p className="mt-2 text-sm text-destructive">{errorMessage(create.error)}</p>}
    </>
  )
}

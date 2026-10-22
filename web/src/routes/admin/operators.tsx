import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ErrorState, Field, Loading, PageHeader, StatusBadge, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'

type Op = { id: number; public_name: string; trade_name: string; status: string; effective_commission_rate: number; commission_rate: number | null; cancellations_count: number; tours_count: number; contact_email: string }

export default function AdminOperators() {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const list = useQuery({ queryKey: ['admin-operators', q], queryFn: () => api<Op[]>(`/admin/operators${q ? `?q=${encodeURIComponent(q)}` : ''}`) })
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ public_name: '', trade_name: '', contact_email: '', contact_phone: '', document: '', cadastur_number: '' })
  const create = useMutation({
    mutationFn: () => api<Op>('/admin/operators', { method: 'POST', body: { ...form, contact_email: form.contact_email || null } }),
    onSuccess: () => {
      setOpen(false)
      setForm({ public_name: '', trade_name: '', contact_email: '', contact_phone: '', document: '', cadastur_number: '' })
      qc.invalidateQueries({ queryKey: ['admin-operators'] })
    },
  })
  return (
    <>
      <PageHeader title="Operadoras" description="Cadastro, comissão individual (padrão 10%) e convites." actions={<Button onClick={() => setOpen(true)}><Plus /> Nova operadora</Button>} />
      <input aria-label="Buscar" placeholder="Buscar por nome…" className={`${inputClass} mb-4 max-w-sm`} value={q} onChange={(e) => setQ(e.target.value)} />
      {list.isLoading ? <Loading /> : list.error ? <ErrorState error={list.error} /> : (
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left"><tr><th className="p-3">Operadora</th><th className="p-3">Status</th><th className="p-3">Comissão</th><th className="p-3">Passeios</th><th className="p-3">Cancelamentos</th></tr></thead>
            <tbody className="divide-y">
              {list.data?.map((o) => (
                <tr key={o.id}>
                  <td className="p-3"><Link className="font-medium text-primary hover:underline" to={`/admin/operadoras/${o.id}`}>{o.public_name}</Link><div className="text-xs text-muted-foreground">{o.trade_name}</div></td>
                  <td className="p-3"><StatusBadge status={o.status} /></td>
                  <td className="p-3 tabular-nums">{(o.effective_commission_rate * 100).toFixed(1)}%{o.commission_rate === null && <span className="text-xs text-muted-foreground"> (padrão)</span>}</td>
                  <td className="p-3">{o.tours_count}</td>
                  <td className="p-3">{o.cancellations_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nova operadora</DialogTitle></DialogHeader>
          <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); create.mutate() }}>
            <Field label="Nome exibido ao turista" htmlFor="o-pn"><input id="o-pn" required className={inputClass} value={form.public_name} onChange={(e) => setForm({ ...form, public_name: e.target.value })} /></Field>
            <Field label="Nome fantasia" htmlFor="o-tn"><input id="o-tn" required className={inputClass} value={form.trade_name} onChange={(e) => setForm({ ...form, trade_name: e.target.value })} /></Field>
            <Field label="CNPJ/CPF" htmlFor="o-doc"><input id="o-doc" className={inputClass} value={form.document} onChange={(e) => setForm({ ...form, document: e.target.value })} /></Field>
            <Field label="Cadastur" htmlFor="o-cad"><input id="o-cad" className={inputClass} value={form.cadastur_number} onChange={(e) => setForm({ ...form, cadastur_number: e.target.value })} /></Field>
            <Field label="E-mail de reservas" htmlFor="o-em"><input id="o-em" type="email" className={inputClass} value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} /></Field>
            <Field label="Telefone" htmlFor="o-ph"><input id="o-ph" className={inputClass} value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} /></Field>
            {create.error && <p className="text-sm text-destructive">{errorMessage(create.error)}</p>}
            <Button type="submit" disabled={create.isPending}>Criar</Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

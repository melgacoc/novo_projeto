import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorState, Field, Loading, PageHeader, StatusBadge, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'
import { dateOnly } from '@/lib/format'

type Detail = {
  id: number; public_name: string; trade_name: string; legal_name: string; document: string; cadastur_number: string; status: string
  commission_rate: number | null; effective_commission_rate: number; contact_phone: string; contact_email: string; cancellations_count: number
  notes: string; gateway_recipient_id: string | null
  members: { user_id: number; email: string; name: string; role: string }[]
  invites: { id: number; email: string; expires_at: string; accepted_at: string | null }[]
  tours: { id: number; title: string; status: string; slug: string }[]
}
const TEXT_FIELDS: [keyof Detail, string][] = [
  ['public_name', 'Nome exibido ao turista'], ['trade_name', 'Nome fantasia'], ['legal_name', 'Razão social'], ['document', 'CNPJ/CPF'],
  ['cadastur_number', 'Cadastur'], ['contact_phone', 'Telefone'], ['contact_email', 'E-mail'], ['gateway_recipient_id', 'ID do recebedor no gateway'],
]

export default function AdminOperatorDetail() {
  const { id } = useParams()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-operator', id], queryFn: () => api<Detail>(`/admin/operators/${id}`) })
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteLink, setInviteLink] = useState('')
  const invite = useMutation({
    mutationFn: () => api<{ link: string }>(`/admin/operators/${id}/invites`, { method: 'POST', body: { email: inviteEmail } }),
    onSuccess: (r) => { setInviteLink(r.link); setInviteEmail(''); qc.invalidateQueries({ queryKey: ['admin-operator', id] }) },
  })
  const [memberEmail, setMemberEmail] = useState('')
  const addMember = useMutation({
    mutationFn: () => api(`/admin/operators/${id}/members`, { method: 'POST', body: { email: memberEmail } }),
    onSuccess: () => { setMemberEmail(''); qc.invalidateQueries({ queryKey: ['admin-operator', id] }) },
  })

  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const d = q.data
  return (
    <>
      <PageHeader title={d.public_name} description={<>Cancelamentos: {d.cancellations_count} · Comissão efetiva: {(d.effective_commission_rate * 100).toFixed(1)}%</>}
        actions={<><StatusBadge status={d.status} /><Button asChild variant="outline"><Link to={`/admin/passeios?operator_id=${d.id}`}>Passeios</Link></Button></>} />
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <OperatorForm key={q.dataUpdatedAt} data={d} onSaved={(nd) => qc.setQueryData(['admin-operator', id], nd)} />

        <div className="space-y-6">
          <section className="space-y-3 rounded-xl border bg-card p-4">
            <h2 className="font-semibold">Usuários da operadora</h2>
            <ul className="text-sm">{d.members.map((m) => <li key={m.user_id}>{m.name || m.email} <span className="text-muted-foreground">({m.email})</span></li>)}</ul>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); addMember.mutate() }}>
              <input type="email" required placeholder="e-mail de usuário existente" aria-label="E-mail do usuário" className={inputClass} value={memberEmail} onChange={(e) => setMemberEmail(e.target.value)} />
              <Button type="submit" size="icon" aria-label="Vincular"><Plus /></Button>
            </form>
            {addMember.error && <p className="text-xs text-destructive">{errorMessage(addMember.error)}</p>}
          </section>
          <section className="space-y-3 rounded-xl border bg-card p-4">
            <h2 className="font-semibold">Convidar por e-mail</h2>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); invite.mutate() }}>
              <input type="email" required placeholder="email@operadora.com" aria-label="E-mail do convite" className={inputClass} value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
              <Button type="submit" disabled={invite.isPending}>Convidar</Button>
            </form>
            {inviteLink && (
              <div className="rounded-md bg-muted p-2 text-xs">
                Link do convite (também enviado por e-mail):
                <div className="mt-1 flex gap-1"><input readOnly value={inviteLink} aria-label="Link" className="flex-1 truncate bg-transparent font-mono" />
                  <Button type="button" size="sm" variant="ghost" onClick={() => navigator.clipboard?.writeText(inviteLink)}><Copy /></Button></div>
              </div>
            )}
            <ul className="text-xs text-muted-foreground">{d.invites.map((i) => <li key={i.id}>{i.email} · {i.accepted_at ? 'aceito' : `expira ${dateOnly(i.expires_at)}`}</li>)}</ul>
          </section>
          <section className="space-y-2 rounded-xl border bg-card p-4">
            <div className="flex items-center justify-between"><h2 className="font-semibold">Passeios</h2>
              <Button asChild size="sm" variant="outline"><Link to={`/admin/passeios/novo?operator_id=${d.id}`}><Plus /> Cadastrar</Link></Button></div>
            <ul className="space-y-1 text-sm">{d.tours.map((t) => <li key={t.id} className="flex items-center justify-between gap-2"><Link className="text-primary hover:underline" to={`/admin/passeios/${t.id}`}>{t.title || t.slug}</Link><StatusBadge status={t.status} /></li>)}</ul>
          </section>
        </div>
      </div>
    </>
  )
}

function OperatorForm({ data, onSaved }: { data: Detail; onSaved: (d: Detail) => void }) {
  const [form, setForm] = useState<Record<string, string>>(() =>
    Object.fromEntries([...TEXT_FIELDS.map(([k]) => [k, String(data[k] ?? '')]), ['status', data.status], ['notes', data.notes]]))
  const [commission, setCommission] = useState(data.commission_rate === null ? '' : String(+(data.commission_rate * 100).toFixed(2)))
  const save = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = { ...form, contact_email: form.contact_email || null, gateway_recipient_id: form.gateway_recipient_id || null }
      if (commission === '') body.reset_commission = true
      else body.commission_rate = (Number(commission.replace(',', '.')) / 100).toFixed(4)
      return api<Detail>(`/admin/operators/${data.id}`, { method: 'PATCH', body })
    },
    onSuccess: onSaved,
  })
  return (
    <form className="grid gap-4 rounded-xl border bg-card p-5 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
          {TEXT_FIELDS.map(([k, label]) => (
            <Field key={k} label={label} htmlFor={`od-${k}`}><input id={`od-${k}`} className={inputClass} value={form[k] ?? ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>
          ))}
          <Field label="Status" htmlFor="od-status">
            <select id="od-status" className={inputClass} value={form.status ?? ''} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="active">Ativa</option><option value="pending_review">Em análise</option><option value="invited">Convidada</option><option value="suspended">Suspensa</option>
            </select>
          </Field>
          <Field label="Comissão individual (%)" htmlFor="od-comm" hint="Vazio = usa a comissão padrão da plataforma">
            <input id="od-comm" inputMode="decimal" className={inputClass} placeholder="padrão" value={commission} onChange={(e) => setCommission(e.target.value)} />
          </Field>
          <div className="sm:col-span-2"><Field label="Notas internas" htmlFor="od-notes"><textarea id="od-notes" className={`${inputClass} h-20 py-2`} value={form.notes ?? ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field></div>
          {save.error && <p className="text-sm text-destructive sm:col-span-2">{errorMessage(save.error)}</p>}
          <div className="flex items-center gap-3 sm:col-span-2"><Button type="submit" disabled={save.isPending}>Salvar</Button>{save.isSuccess && <span className="text-sm text-emerald-700">Salvo.</span>}</div>
        </form>
  )
}

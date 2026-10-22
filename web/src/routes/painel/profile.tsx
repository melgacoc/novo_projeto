import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { ErrorState, Field, Loading, PageHeader, StatusBadge, inputClass } from '@/components/common'
import { api } from '@/lib/api'
import { useSession } from '@/lib/session-context'

type Profile = { id: number; public_name: string; trade_name: string; legal_name: string; document: string; cadastur_number: string; status: string; contact_phone: string; contact_email: string; commission_rate: number }
const FIELDS: [keyof Profile, string, string?][] = [
  ['trade_name', 'Nome fantasia (aparece no voucher)'],
  ['legal_name', 'Razão social'],
  ['document', 'CNPJ ou CPF'],
  ['cadastur_number', 'Número do Cadastur'],
  ['contact_phone', 'Telefone/WhatsApp (só no voucher)'],
  ['contact_email', 'E-mail para reservas (recebe os avisos)'],
]

export default function PainelProfile() {
  const { operatorId } = useSession()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['op-profile', operatorId], queryFn: () => api<Profile>('/operator/profile') })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  return <ProfileForm key={q.dataUpdatedAt} data={q.data} onSaved={(p) => qc.setQueryData(['op-profile', operatorId], p)} />
}

function ProfileForm({ data, onSaved }: { data: Profile; onSaved: (p: Profile) => void }) {
  const [form, setForm] = useState<Partial<Profile>>(data)
  const save = useMutation({
    mutationFn: () => api<Profile>('/operator/profile', { method: 'PATCH', body: Object.fromEntries(FIELDS.map(([k]) => [k, form[k] ?? ''])) }),
    onSuccess: onSaved,
  })
  const q = { data }
  return (
    <>
      <PageHeader title="Perfil da operadora" description={<>Nome exibido aos turistas: <strong>{q.data.public_name}</strong> (alterado pela plataforma) · Comissão: {(q.data.commission_rate * 100).toFixed(1)}%</>}
        actions={<StatusBadge status={q.data.status} />} />
      <form className="grid max-w-2xl gap-4 rounded-xl border bg-card p-5" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        {FIELDS.map(([k, label]) => (
          <Field key={k} label={label} htmlFor={`p-${k}`}>
            <input id={`p-${k}`} className={inputClass} type={k === 'contact_email' ? 'email' : 'text'} value={String(form[k] ?? '')} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
          </Field>
        ))}
        {save.error && <ErrorState error={save.error} />}
        <div className="flex items-center gap-3"><Button type="submit" disabled={save.isPending}>Salvar</Button>{save.isSuccess && <span className="text-sm text-emerald-700">Salvo.</span>}</div>
      </form>
    </>
  )
}

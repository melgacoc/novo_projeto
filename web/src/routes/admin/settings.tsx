import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { ErrorState, Field, Loading, PageHeader, inputClass } from '@/components/common'
import { errorMessage } from '@/lib/messages'
import { api } from '@/lib/api'

type S = { default_commission_rate: string; hold_minutes: string; payout_delay_days: string; low_availability_min_seats: string }

export default function AdminSettings() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-settings'], queryFn: () => api<S>('/admin/settings') })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  return <SettingsForm key={q.dataUpdatedAt} data={q.data} onSaved={(d) => { qc.setQueryData(['admin-settings'], d); qc.invalidateQueries({ queryKey: ['config'] }) }} />
}

function SettingsForm({ data, onSaved }: { data: S; onSaved: (d: S) => void }) {
  const [f, setF] = useState<S>(data)
  const [pct, setPct] = useState(String(+(Number(data.default_commission_rate) * 100).toFixed(2)))
  const save = useMutation({
    mutationFn: () => api<S>('/admin/settings', { method: 'PATCH', body: {
      default_commission_rate: (Number(pct.replace(',', '.')) / 100).toFixed(4),
      hold_minutes: Number(f.hold_minutes), payout_delay_days: Number(f.payout_delay_days), low_availability_min_seats: Number(f.low_availability_min_seats),
    } }),
    onSuccess: onSaved,
  })
  return (
    <>
      <PageHeader title="Configurações da plataforma" description="Valores usados em novas reservas (reservas existentes mantêm os valores congelados)." />
      <form className="grid max-w-xl gap-4 rounded-xl border bg-card p-5" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <Field label="Comissão padrão (%)" htmlFor="s-comm" hint="Operadoras sem comissão individual usam este valor">
          <input id="s-comm" inputMode="decimal" className={inputClass} value={pct} onChange={(e) => setPct(e.target.value)} />
        </Field>
        <Field label="Tempo para pagar (minutos)" htmlFor="s-hold" hint="Quanto tempo a vaga fica retida no checkout">
          <input id="s-hold" type="number" min={5} max={60} className={inputClass} value={f.hold_minutes} onChange={(e) => setF({ ...f, hold_minutes: e.target.value })} />
        </Field>
        <Field label="Prazo de repasse (dias após o passeio)" htmlFor="s-pay">
          <input id="s-pay" type="number" min={0} className={inputClass} value={f.payout_delay_days} onChange={(e) => setF({ ...f, payout_delay_days: e.target.value })} />
        </Field>
        <Field label='Mínimo de vagas para "últimas vagas"' htmlFor="s-low">
          <input id="s-low" type="number" min={0} className={inputClass} value={f.low_availability_min_seats} onChange={(e) => setF({ ...f, low_availability_min_seats: e.target.value })} />
        </Field>
        {save.error && <p className="text-sm text-destructive">{errorMessage(save.error)}</p>}
        <div className="flex items-center gap-3"><Button type="submit" disabled={save.isPending}>Salvar</Button>{save.isSuccess && <span className="text-sm text-emerald-700">Salvo.</span>}</div>
      </form>
    </>
  )
}

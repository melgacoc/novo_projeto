import { useSearchParams, useNavigate } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { ErrorState, PageHeader } from '@/components/common'
import { api } from '@/lib/api'
import { useSession } from '@/lib/session-context'

export default function Invite() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const s = useSession()
  const accept = useMutation({
    mutationFn: () => api<{ operator_id: number }>('/operator/invites/accept', { method: 'POST', body: { token: params.get('token') } }),
    onSuccess: (r) => {
      s.setOperatorId(r.operator_id)
      qc.invalidateQueries({ queryKey: ['me'] })
      navigate('/painel')
    },
  })
  return (
    <>
      <PageHeader title="Convite de operadora" description="Aceite para gerenciar os passeios desta operadora." />
      {accept.error && <div className="mb-3"><ErrorState error={accept.error} /></div>}
      <Button disabled={!params.get('token') || accept.isPending} onClick={() => accept.mutate()}>Aceitar convite</Button>
    </>
  )
}

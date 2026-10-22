import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, Pause } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorState, Loading, PageHeader } from '@/components/common'
import { TourEditor } from '@/components/TourEditor'
import { api } from '@/lib/api'
import type { TourFull } from '@/lib/types'

export default function PainelTourEdit() {
  const { id } = useParams()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['tour', Number(id)], queryFn: () => api<TourFull>(`/operator/tours/${id}`) })
  const pause = useMutation({
    mutationFn: () => api<TourFull>(`/operator/tours/${id}/pause`, { method: 'POST' }),
    onSuccess: (t) => qc.setQueryData(['tour', Number(id)], t),
  })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const t = q.data
  return (
    <>
      <PageHeader title={t.title || 'Passeio'} actions={
        <>
          {t.status === 'published' && <Button variant="outline" asChild><Link to={`/pt/passeios/${t.slug}`} target="_blank"><ExternalLink /> Ver no site</Link></Button>}
          {t.status === 'published' && <Button variant="outline" onClick={() => pause.mutate()}><Pause /> Pausar vendas</Button>}
        </>
      } />
      <TourEditor key={`${t.id}-${t.updated_at}`} tour={t} mode="operator" onSaved={(nt) => qc.setQueryData(['tour', nt.id], nt)} />
    </>
  )
}

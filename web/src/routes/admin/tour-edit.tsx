import { Link, useParams } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ErrorState, Loading, PageHeader } from '@/components/common'
import { TourEditor } from '@/components/TourEditor'
import { api } from '@/lib/api'
import type { TourFull } from '@/lib/types'

export default function AdminTourEdit() {
  const { id } = useParams()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['tour', Number(id)], queryFn: () => api<TourFull>(`/admin/tours/${id}`) })
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  return (
    <>
      <PageHeader title={`Editar: ${q.data.title || q.data.slug}`} description={<>Edição concierge em nome de {q.data.operator_name}. <Link className="text-primary underline" to={`/admin/passeios/${id}`}>Voltar à análise</Link></>} />
      <TourEditor key={`${q.data.id}-${q.data.updated_at}`} tour={q.data} mode="admin" onSaved={(t) => qc.setQueryData(['tour', t.id], t)} />
    </>
  )
}

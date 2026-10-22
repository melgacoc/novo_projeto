import { useNavigate } from 'react-router'
import { PageHeader } from '@/components/common'
import { TourEditor } from '@/components/TourEditor'

export default function PainelTourNew() {
  const navigate = useNavigate()
  return (
    <>
      <PageHeader title="Novo passeio" description="Preencha as informações básicas, os textos e os preços. Fotos e agenda vêm em seguida." />
      <TourEditor mode="operator" onSaved={(t) => navigate(`/painel/passeios/${t.id}`, { replace: true })} />
    </>
  )
}

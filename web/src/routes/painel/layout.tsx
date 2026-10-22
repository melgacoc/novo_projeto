import { BarChart3, CalendarDays, CircleUser, Map, ReceiptText, Ticket } from 'lucide-react'
import { AreaLayout, ClientOnlyFallback } from '@/components/AreaLayout'

// painel só no navegador: o servidor entrega o fallback e o resto roda no cliente
export async function clientLoader() {
  return null
}
clientLoader.hydrate = true as const

export function HydrateFallback() {
  return <ClientOnlyFallback />
}

export function meta() {
  return [{ title: 'Painel da operadora' }, { name: 'robots', content: 'noindex' }]
}

export default function PainelLayout() {
  return (
    <AreaLayout
      title="Painel"
      roles={['operator', 'admin']}
      items={[
        { to: '/painel', label: 'Início', icon: <BarChart3 />, end: true },
        { to: '/painel/passeios', label: 'Passeios', icon: <Map /> },
        { to: '/painel/agenda', label: 'Agenda', icon: <CalendarDays /> },
        { to: '/painel/reservas', label: 'Reservas', icon: <Ticket /> },
        { to: '/painel/extrato', label: 'Extrato', icon: <ReceiptText /> },
        { to: '/painel/perfil', label: 'Perfil', icon: <CircleUser /> },
      ]}
    />
  )
}

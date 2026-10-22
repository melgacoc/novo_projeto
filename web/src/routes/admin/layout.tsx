import { BarChart3, Building2, FolderTree, History, Map, Settings, Ticket, Users, Wallet } from 'lucide-react'
import { AreaLayout, ClientOnlyFallback } from '@/components/AreaLayout'

export async function clientLoader() {
  return null
}
clientLoader.hydrate = true as const

export function HydrateFallback() {
  return <ClientOnlyFallback />
}

export function meta() {
  return [{ title: 'Admin' }, { name: 'robots', content: 'noindex' }]
}

export default function AdminLayout() {
  return (
    <AreaLayout
      title="Admin"
      roles={['admin']}
      items={[
        { to: '/admin', label: 'Visão geral', icon: <BarChart3 />, end: true },
        { to: '/admin/passeios', label: 'Passeios', icon: <Map /> },
        { to: '/admin/operadoras', label: 'Operadoras', icon: <Building2 /> },
        { to: '/admin/reservas', label: 'Reservas', icon: <Ticket /> },
        { to: '/admin/repasses', label: 'Repasses', icon: <Wallet /> },
        { to: '/admin/categorias', label: 'Categorias', icon: <FolderTree /> },
        { to: '/admin/usuarios', label: 'Usuários', icon: <Users /> },
        { to: '/admin/configuracoes', label: 'Configurações', icon: <Settings /> },
        { to: '/admin/auditoria', label: 'Auditoria', icon: <History /> },
      ]}
    />
  )
}

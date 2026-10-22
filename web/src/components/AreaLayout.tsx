import { useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet } from 'react-router'
import { Compass, Menu, X } from 'lucide-react'
import { Loading } from '@/components/common'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useSession } from '@/lib/session-context'
import type { Role } from '@/lib/api'
import { cn } from '@/lib/utils'

export type NavItem = { to: string; label: string; icon: ReactNode; end?: boolean }

/** Layout com menu lateral para o painel da operadora e o admin (base: AdminLayout/SidebarNav do Rio Manager). */
export function AreaLayout({ title, items, roles }: { title: string; items: NavItem[]; roles: Role[] }) {
  const s = useSession()
  const [open, setOpen] = useState(false)

  let gate: ReactNode = null
  if (!s.ready || s.meLoading) gate = <Loading />
  else if (s.authEnabled && !s.me)
    gate = <p>Faça login para continuar. <Link className="text-primary underline" to={`/pt/entrar?next=${encodeURIComponent(typeof window !== 'undefined' ? window.location.pathname : '/')}`}>Entrar</Link></p>
  else if (!s.me || !roles.includes(s.me.role))
    gate = s.authEnabled
      ? <p>Seu usuário não tem acesso a esta área.</p>
      : <p>Esta área é para {roles.includes('operator') ? 'operadoras' : 'administradores'}. Troque o papel no seletor amarelo no topo da página.</p>
  else if (roles.includes('operator') && !s.me.operators.length)
    gate = <p>Nenhuma operadora vinculada ao seu usuário. Peça um convite à equipe da plataforma.</p>

  const nav = (
    <nav className="flex flex-col gap-0.5 p-3">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.end} onClick={() => setOpen(false)}
          className={({ isActive }) => cn('flex items-center gap-2 rounded-md px-3 py-2 text-sm [&_svg]:size-4', isActive ? 'bg-primary/10 font-semibold text-primary' : 'hover:bg-accent')}>
          {i.icon} {i.label}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r bg-card md:block">
        <Link to="/" className="flex h-14 items-center gap-2 border-b px-4 font-bold text-primary"><Compass className="size-5" />{title}</Link>
        {nav}
        <div className="px-3"><ThemeToggle /></div>
      </aside>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal>
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-card shadow-xl">
            <div className="flex h-14 items-center justify-between border-b px-4 font-bold text-primary">{title}
              <Button variant="ghost" size="icon" aria-label="Fechar menu" onClick={() => setOpen(false)}><X /></Button>
            </div>
            {nav}
          </aside>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <header className="flex h-14 items-center gap-2 border-b bg-card px-4 md:hidden">
          <Button variant="ghost" size="icon" aria-label="Abrir menu" onClick={() => setOpen(true)}><Menu /></Button>
          <span className="font-semibold">{title}</span>
          <span className="ml-auto"><ThemeToggle /></span>
        </header>
        <main className="mx-auto max-w-6xl p-4 sm:p-6">{gate ?? <Outlet />}</main>
      </div>
    </div>
  )
}

export function ClientOnlyFallback() {
  return <div className="p-10"><Loading /></div>
}

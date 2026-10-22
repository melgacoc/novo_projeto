import { Link, NavLink, Outlet, data, useLocation } from 'react-router'
import { Compass, LogIn, LogOut, Ticket } from 'lucide-react'
import type { Route } from './+types/layout'
import { FlagBR, FlagES, FlagUS } from '@/components/ui/flags'
import { ThemeToggle } from '@/components/ThemeToggle'
import { LANGS, asLang, t, useLang } from '@/lib/i18n'
import { useSession } from '@/lib/session-context'
import type { Lang } from '@/lib/types'

export function loader({ params }: Route.LoaderArgs) {
  if (!LANGS.includes(params.lang as Lang)) throw data(null, { status: 404 })
  return { lang: asLang(params.lang) }
}

const FLAGS = { pt: FlagBR, es: FlagES, en: FlagUS }

function LangSwitcher() {
  const lang = useLang()
  const loc = useLocation()
  const rest = loc.pathname.split('/').slice(2).join('/')
  return (
    <div className="flex items-center gap-1" aria-label="Idioma">
      {LANGS.map((l) => {
        const Flag = FLAGS[l]
        return (
          <Link
            key={l}
            to={`/${l}${rest ? `/${rest}` : ''}${loc.search}`}
            aria-current={l === lang ? 'true' : undefined}
            title={l.toUpperCase()}
            className={`rounded p-1 ${l === lang ? 'ring-2 ring-primary' : 'opacity-60 hover:opacity-100'}`}
          >
            <Flag className="h-3.5 w-5 rounded-sm" />
          </Link>
        )
      })}
    </div>
  )
}

export default function PublicLayout() {
  const lang = useLang()
  const s = useSession()
  const signedIn = s.authEnabled ? !!s.me : true
  const nav = 'flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm hover:bg-accent'
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
          <Link to={`/${lang}`} className="mr-auto flex items-center gap-2 font-bold text-primary">
            <Compass className="size-5" /> {s.config?.app_name ?? 'Tur'}
          </Link>
          <NavLink to={`/${lang}/passeios`} className={nav}>{t(lang, 'nav.tours')}</NavLink>
          {signedIn && (
            <NavLink to={`/${lang}/reservas`} className={nav}><Ticket className="size-4" /><span className="hidden sm:inline">{t(lang, 'nav.bookings')}</span></NavLink>
          )}
          {s.authEnabled && !s.me && (
            <NavLink to={`/${lang}/entrar`} className={nav}><LogIn className="size-4" /><span className="hidden sm:inline">{t(lang, 'nav.login')}</span></NavLink>
          )}
          {s.authEnabled && s.me && (
            <button type="button" onClick={() => s.logout()} className={nav}><LogOut className="size-4" /><span className="hidden sm:inline">{t(lang, 'nav.logout')}</span></button>
          )}
          <LangSwitcher />
          <ThemeToggle />
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground">
          <span>{t(lang, 'footer.secure')}</span>
          <nav className="flex gap-4">
            <Link to={`/${lang}/termos`} className="hover:underline">{t(lang, 'footer.terms')}</Link>
            <Link to={`/${lang}/privacidade`} className="hover:underline">{t(lang, 'footer.privacy')}</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}

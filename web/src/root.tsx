import { useEffect, useState } from 'react'
import { isRouteErrorResponse, Links, Meta, Outlet, Scripts, ScrollRestoration, useParams } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource-variable/geist'
import './index.css'
import type { Route } from './+types/root'
import { SessionProvider } from '@/lib/session'
import { DevRoleBar } from '@/components/DevRoleBar'
import { asLang } from '@/lib/i18n'

export const links: Route.LinksFunction = () => [
  { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
  { rel: 'manifest', href: '/manifest.webmanifest' },
]

const THEME_SCRIPT = `try{var t=localStorage.getItem('tur.theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`

export function Layout({ children }: { children: React.ReactNode }) {
  const { lang } = useParams()
  const htmlLang = { pt: 'pt-BR', es: 'es', en: 'en' }[asLang(lang)]
  return (
    <html lang={htmlLang} suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0284c7" />
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  )
}

export default function App() {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: true, retry: 1 } } }),
  )
  useEffect(() => {
    // PWA: registra o service worker só em produção (em desenvolvimento atrapalha o recarregamento)
    if (import.meta.env.PROD && 'serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {})
  }, [])
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <DevRoleBar />
        <Outlet />
      </SessionProvider>
    </QueryClientProvider>
  )
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let title = 'Algo deu errado'
  let details = 'Tente novamente em instantes.'
  if (isRouteErrorResponse(error)) {
    title = error.status === 404 ? 'Página não encontrada' : `Erro ${error.status}`
    details = error.status === 404 ? 'O endereço que você abriu não existe.' : error.statusText || details
  } else if (import.meta.env.DEV && error instanceof Error) {
    details = error.message
  }
  return (
    <main className="mx-auto max-w-xl p-8 text-center">
      <h1 className="mb-2 text-2xl font-semibold">{title}</h1>
      <p className="mb-6 text-muted-foreground">{details}</p>
      <a href="/" className="text-primary underline">Voltar ao início</a>
    </main>
  )
}

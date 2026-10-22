import type { Route } from './+types/robots'

export function loader({ request }: Route.LoaderArgs) {
  const origin = new URL(request.url).origin
  const body = `User-agent: *\nDisallow: /painel\nDisallow: /admin\nDisallow: /*/checkout\nDisallow: /*/reservas\nSitemap: ${origin}/sitemap.xml\n`
  return new Response(body, { headers: { 'Content-Type': 'text/plain' } })
}

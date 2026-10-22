import { api } from '@/lib/api'
import type { Route } from './+types/sitemap'

export async function loader({ request }: Route.LoaderArgs) {
  const origin = new URL(request.url).origin
  const data = await api<{ tours: { slug: string; updated_at: string }[]; categories: string[] }>('/sitemap')
  const urls: string[] = []
  for (const l of ['pt', 'es', 'en']) {
    urls.push(`${origin}/${l}`, `${origin}/${l}/passeios`)
    data.categories.forEach((c) => urls.push(`${origin}/${l}/passeios?category=${c}`))
    data.tours.forEach((t) => urls.push(`${origin}/${l}/passeios/${t.slug}`))
  }
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls
    .map((u) => `  <url><loc>${u.replace(/&/g, '&amp;')}</loc></url>`)
    .join('\n')}\n</urlset>`
  return new Response(body, { headers: { 'Content-Type': 'application/xml', 'Cache-Control': 'public, max-age=3600' } })
}

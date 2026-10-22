import { redirect } from 'react-router'
import type { Route } from './+types/index'

// "/" -> idioma do navegador (pt, es ou en)
export function loader({ request }: Route.LoaderArgs) {
  const header = (request.headers.get('accept-language') ?? '').toLowerCase()
  const lang = header.startsWith('es') ? 'es' : header.startsWith('en') ? 'en' : 'pt'
  return redirect(`/${lang}`)
}

export default function Index() {
  return null
}

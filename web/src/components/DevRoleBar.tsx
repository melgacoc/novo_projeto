import { Link } from 'react-router'
import { FlaskConical } from 'lucide-react'
import { useSession } from '@/lib/session-context'
import { API_URL, type Role } from '@/lib/api'

const ROLES: { value: Role; label: string; home: string }[] = [
  { value: 'tourist', label: 'Turista', home: '/pt' },
  { value: 'operator', label: 'Operadora', home: '/painel' },
  { value: 'admin', label: 'Admin', home: '/admin' },
]

/** Barra fixa do modo sem login (AUTH_ENABLED=false): escolhe o papel e a operadora usados nas requisições. */
export function DevRoleBar() {
  const s = useSession()
  if (s.configError) {
    return (
      <div role="alert" className="sticky top-0 z-50 border-b border-red-300 bg-red-100 px-4 py-1.5 text-xs text-red-900">
        Não foi possível conectar à API em <code>{API_URL}</code>. Verifique se a API está rodando (<code>make api</code>) e se esse endereço abre no navegador.
      </div>
    )
  }
  if (!s.config || s.authEnabled) return null
  const ops = s.me?.operators ?? []
  return (
    <div className="sticky top-0 z-50 flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-amber-300 bg-amber-100 px-4 py-1.5 text-xs text-amber-950">
      <span className="flex items-center gap-1 font-semibold">
        <FlaskConical className="size-3.5" /> Modo sem login
      </span>
      <label className="flex items-center gap-1">
        Papel:
        <select
          aria-label="Papel de desenvolvimento"
          className="rounded border border-amber-300 bg-white px-1 py-0.5"
          value={s.devRole}
          onChange={(e) => s.setDevRole(e.target.value as Role)}
        >
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </label>
      {(s.devRole === 'operator' || s.devRole === 'admin') && ops.length > 0 && (
        <label className="flex items-center gap-1">
          Operadora:
          <select
            aria-label="Operadora"
            className="max-w-48 rounded border border-amber-300 bg-white px-1 py-0.5"
            value={s.operatorId ?? ''}
            onChange={(e) => s.setOperatorId(e.target.value ? Number(e.target.value) : null)}
          >
            {ops.map((o) => (
              <option key={o.id} value={o.id}>{o.public_name}</option>
            ))}
          </select>
        </label>
      )}
      <nav className="ml-auto flex gap-3">
        <Link className="underline" to="/pt">Site</Link>
        <Link className="underline" to="/painel">Painel</Link>
        <Link className="underline" to="/admin">Admin</Link>
        {s.config.payment_gateway === 'fake' && (
          <a className="underline" href="http://localhost:8026" target="_blank" rel="noreferrer">E-mails (Mailpit)</a>
        )}
      </nav>
    </div>
  )
}

// Cliente da API (base: lib/api.ts do Rio Manager, adaptado).
// - Navegador: access token em memória; refresh por cookie httpOnly (credentials: 'include') + CSRF.
// - Login desligado (AUTH_ENABLED=false): envia X-Dev-User-Role com o papel escolhido no seletor.
// - Servidor (SSR): só chama rotas públicas.

const isServer = typeof window === 'undefined'

export const API_URL: string = isServer
  ? process.env.API_URL_INTERNAL || import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  : import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number
  code: string
  details?: Record<string, unknown>

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

// ---------------------------------------------------------------------------
// Estado da sessão no navegador
// ---------------------------------------------------------------------------
export type Role = 'tourist' | 'operator' | 'admin'

const state: {
  accessToken: string | null
  authEnabled: boolean | null
  devRole: Role
  operatorId: number | null
} = { accessToken: null, authEnabled: null, devRole: 'tourist', operatorId: null }

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, value)
  } catch {
    /* modo privado: segue sem persistir */
  }
}

if (!isServer) {
  const r = readStorage('tur.devRole')
  if (r === 'tourist' || r === 'operator' || r === 'admin') state.devRole = r
  const op = readStorage('tur.operatorId')
  if (op && /^\d+$/.test(op)) state.operatorId = Number(op)
}

export const session = {
  setAuthEnabled(v: boolean) {
    state.authEnabled = v
  },
  get authEnabled() {
    return state.authEnabled
  },
  get devRole() {
    return state.devRole
  },
  setDevRole(role: Role) {
    state.devRole = role
    writeStorage('tur.devRole', role)
  },
  get operatorId() {
    return state.operatorId
  },
  setOperatorId(id: number | null) {
    state.operatorId = id
    writeStorage('tur.operatorId', id === null ? null : String(id))
  },
  setAccessToken(token: string | null) {
    state.accessToken = token
  },
  get accessToken() {
    return state.accessToken
  },
}

export function csrfToken(): string | null {
  if (isServer) return null
  const m = document.cookie.match(/(?:^|; )tur_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : null
}

// uma renovação por vez: requisições simultâneas que recebem 401 esperam a mesma
let refreshing: Promise<boolean> | null = null

export async function refreshSession(): Promise<boolean> {
  const csrf = csrfToken()
  if (!csrf) return false
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${API_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'X-CSRF-Token': csrf },
        })
        if (!res.ok) {
          state.accessToken = null
          return false
        }
        const data = await res.json()
        state.accessToken = data.access_token
        return true
      } catch {
        return false
      } finally {
        setTimeout(() => (refreshing = null), 0)
      }
    })()
  }
  return refreshing
}

// ---------------------------------------------------------------------------
// Requisições
// ---------------------------------------------------------------------------
export type RequestOptions = {
  method?: string
  body?: unknown
  form?: FormData
  locale?: string
  headers?: Record<string, string>
  signal?: AbortSignal
}

async function raw(path: string, opts: RequestOptions, retry: boolean): Promise<Response> {
  const headers: Record<string, string> = { ...(opts.headers ?? {}) }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (opts.locale) headers['Accept-Language'] = opts.locale
  if (!isServer) {
    if (state.authEnabled === false) headers['X-Dev-User-Role'] = state.devRole
    else if (state.accessToken) headers['Authorization'] = `Bearer ${state.accessToken}`
    if (state.operatorId && !headers['X-Operator-Id']) headers['X-Operator-Id'] = String(state.operatorId)
  }
  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? 'GET',
    headers,
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
    credentials: isServer ? undefined : 'include',
    signal: opts.signal,
  })
  if (res.status === 401 && retry && !isServer && state.authEnabled) {
    if (await refreshSession()) return raw(path, opts, false)
  }
  return res
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res: Response
  try {
    res = await raw(path, opts, true)
  } catch {
    throw new ApiError(0, 'network', 'Não foi possível falar com o servidor')
  }
  if (res.status === 204) return undefined as T
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const err = data?.error ?? {}
    throw new ApiError(res.status, err.code ?? 'error', err.message ?? 'Erro na requisição', err.details)
  }
  return data as T
}

export const apiUrl = (path: string) => `${API_URL}${path}`

/** Baixa um arquivo autenticado (ex.: voucher em PDF) e abre em nova aba. */
export async function openFile(path: string) {
  const res = await raw(path, {}, true)
  if (!res.ok) throw new ApiError(res.status, 'download', 'Não foi possível baixar o arquivo')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

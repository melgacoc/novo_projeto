import { createContext, useContext } from 'react'
import type { Role } from './api'
import type { AppConfig, Me } from './types'

export type SessionValue = {
  config: AppConfig | undefined
  configError: boolean
  ready: boolean
  me: Me | undefined
  meLoading: boolean
  authEnabled: boolean
  devRole: Role
  operatorId: number | null
  setDevRole: (r: Role) => void
  setOperatorId: (id: number | null) => void
  signedIn: (accessToken: string) => void
  logout: () => Promise<void>
}

export const SessionContext = createContext<SessionValue | null>(null)

export function useSession(): SessionValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession fora do SessionProvider')
  return ctx
}

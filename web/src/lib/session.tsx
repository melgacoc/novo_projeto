import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, csrfToken, refreshSession, session, type Role } from './api'
import { SessionContext, type SessionValue } from './session-context'
import type { AppConfig, Me } from './types'


export function SessionProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const config = useQuery({ queryKey: ['config'], queryFn: () => api<AppConfig>('/config'), staleTime: Infinity })
  const [refreshDone, setRefreshDone] = useState(false)
  // no servidor é sempre "tourist"; no navegador lê o localStorage (a barra de papel só aparece depois do /config)
  const [devRole, setDevRoleState] = useState<Role>(() => session.devRole)
  const [chosenOperator, setChosenOperator] = useState<number | null>(() => session.operatorId)
  const [authVersion, setAuthVersion] = useState(0)
  const authEnabled = config.data?.auth_enabled ?? false
  const ready = !!config.data && (!config.data.auth_enabled || refreshDone)

  if (config.data) session.setAuthEnabled(config.data.auth_enabled)

  useEffect(() => {
    if (!config.data?.auth_enabled) return
    refreshSession().finally(() => setRefreshDone(true))
  }, [config.data?.auth_enabled])

  const me = useQuery({
    queryKey: ['me', authEnabled ? `auth-${authVersion}` : `dev-${devRole}`],
    queryFn: () => api<Me>('/me'),
    enabled: ready && (!authEnabled || !!session.accessToken),
    retry: false,
    staleTime: 60_000,
  })

  // operadora ativa: a escolhida, se o usuário ainda pertencer a ela; senão a primeira vinculada
  const ops = me.data?.operators ?? []
  const operatorId = ops.some((o) => o.id === chosenOperator) ? chosenOperator : (ops[0]?.id ?? chosenOperator)
  // o cliente da API lê este valor; precisa estar certo antes das consultas dos filhos
  if (operatorId !== session.operatorId) session.setOperatorId(operatorId)

  const setDevRole = useCallback(
    (r: Role) => {
      session.setDevRole(r)
      session.setOperatorId(null)
      setDevRoleState(r)
      setChosenOperator(null)
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'config' })
    },
    [qc],
  )

  const setOperatorId = useCallback(
    (id: number | null) => {
      session.setOperatorId(id)
      setChosenOperator(id)
      qc.removeQueries({ predicate: (q) => !['config', 'me'].includes(String(q.queryKey[0])) })
    },
    [qc],
  )

  const signedIn = useCallback((accessToken: string) => {
    session.setAccessToken(accessToken)
    setAuthVersion((v) => v + 1)
  }, [])

  const logout = useCallback(async () => {
    try {
      await api('/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken() ?? '' } })
    } catch {
      /* segue limpando a sessão local */
    }
    session.setAccessToken(null)
    session.setOperatorId(null)
    setChosenOperator(null)
    setAuthVersion((v) => v + 1)
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'config' })
  }, [qc])

  const value = useMemo<SessionValue>(
    () => ({
      config: config.data,
      configError: config.isError,
      ready,
      me: me.data,
      meLoading: me.isLoading,
      authEnabled,
      devRole,
      operatorId,
      setDevRole,
      setOperatorId,
      signedIn,
      logout,
    }),
    [config.data, config.isError, ready, me.data, me.isLoading, authEnabled, devRole, operatorId, setDevRole, setOperatorId, signedIn, logout],
  )
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

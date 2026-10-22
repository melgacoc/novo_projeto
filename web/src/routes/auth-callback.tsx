import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { refreshSession, session } from '@/lib/api'
import { useSession } from '@/lib/session-context'
import { Loading } from '@/components/common'

// volta do login com Google: o cookie de sessão já foi gravado pela API; troca por um access token
export default function AuthCallback() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const s = useSession()
  const [error, setError] = useState(params.get('error'))
  useEffect(() => {
    if (error || !s.config) return
    refreshSession().then((ok) => {
      if (!ok) return setError('session')
      s.signedIn(session.accessToken ?? '')
      const next = params.get('next') ?? '/'
      navigate(next.startsWith('/') ? next : '/', { replace: true })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.config])
  if (error) return <p className="p-10 text-center">Não foi possível entrar ({error}). <a className="text-primary underline" href="/">Voltar</a></p>
  return <div className="p-10"><Loading label="Entrando…" /></div>
}

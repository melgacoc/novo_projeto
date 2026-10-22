import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import type { Route } from './+types/login'
import { Button } from '@/components/ui/button'
import { ErrorState, Field, inputClass } from '@/components/common'
import { api, apiUrl } from '@/lib/api'
import { asLang, t, useLang } from '@/lib/i18n'
import { useSession } from '@/lib/session-context'

export function meta({ params }: Route.MetaArgs) {
  return [{ title: t(asLang(params.lang), 'login.title') }, { name: 'robots', content: 'noindex' }]
}

export default function Login() {
  const lang = useLang()
  const s = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next')?.startsWith('/') ? params.get('next')! : `/${lang}`
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [sent, setSent] = useState(false)

  const request = useMutation({
    mutationFn: () => api('/auth/email/request-code', { method: 'POST', body: { email, locale: lang } }),
    onSuccess: () => setSent(true),
  })
  const verify = useMutation({
    mutationFn: () => api<{ access_token: string }>('/auth/email/verify', { method: 'POST', body: { email, code, locale: lang } }),
    onSuccess: (r) => {
      s.signedIn(r.access_token)
      navigate(next)
    },
  })

  return (
    <div className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-2xl font-semibold">{t(lang, 'login.title')}</h1>
      {!s.authEnabled ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm">{t(lang, 'login.disabled')}</p>
      ) : (
        <div className="space-y-6">
          {s.config?.google_login && (
            <Button asChild size="lg" variant="outline" className="w-full">
              <a href={apiUrl(`/auth/google/start?next=${encodeURIComponent(next)}`)}>
                <svg viewBox="0 0 48 48" className="size-5" aria-hidden><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
                {t(lang, 'login.google')}
              </a>
            </Button>
          )}
          <p className="text-center text-sm text-muted-foreground">{t(lang, 'login.or')}</p>
          {!sent ? (
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); request.mutate() }}>
              <Field label={t(lang, 'login.email')} htmlFor="email">
                <input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
              </Field>
              {request.error && <ErrorState error={request.error} />}
              <Button type="submit" className="w-full" disabled={request.isPending}>{t(lang, 'login.send')}</Button>
            </form>
          ) : (
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); verify.mutate() }}>
              <Field label={t(lang, 'login.code')} htmlFor="code" hint={email}>
                <input id="code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required autoComplete="one-time-code"
                  value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} className={`${inputClass} text-center font-mono text-lg tracking-widest`} />
              </Field>
              {verify.error && <ErrorState error={verify.error} />}
              <Button type="submit" className="w-full" disabled={verify.isPending}>{t(lang, 'login.verify')}</Button>
            </form>
          )}
        </div>
      )}
    </div>
  )
}

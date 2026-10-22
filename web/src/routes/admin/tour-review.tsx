import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Check, ExternalLink, Pause, Pencil, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorState, Loading, PageHeader, Photo, StatusBadge, textareaClass } from '@/components/common'
import { errorMessage, problemLabel } from '@/lib/messages'
import { TourEditor } from '@/components/TourEditor'
import { api } from '@/lib/api'
import { money } from '@/lib/format'
import type { TourFull } from '@/lib/types'

export default function AdminTourReview() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isNew = id === 'novo'
  const q = useQuery({ queryKey: ['tour', Number(id)], queryFn: () => api<TourFull>(`/admin/tours/${id}`), enabled: !isNew })
  const [notes, setNotes] = useState('')
  const act = useMutation({
    mutationFn: (action: 'approve' | 'reject' | 'pause') => api<TourFull>(`/admin/tours/${id}/${action}`, { method: 'POST', body: { notes } }),
    onSuccess: (t) => { qc.setQueryData(['tour', t.id], t); qc.invalidateQueries({ queryKey: ['admin-tours'] }) },
  })

  if (isNew) {
    return (
      <>
        <PageHeader title="Cadastrar passeio (concierge)" description="Cadastro feito pela equipe em nome da operadora." />
        <TourEditor mode="admin" operatorId={Number(params.get('operator_id'))} onSaved={(t) => navigate(`/admin/passeios/${t.id}/editar`, { replace: true })} />
      </>
    )
  }
  if (q.isLoading) return <Loading />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const t = q.data
  const pt = t.translations.find((x) => x.locale === 'pt')
  return (
    <>
      <PageHeader title={t.title || t.slug} description={<>Operadora: <Link className="text-primary underline" to={`/admin/operadoras/${t.operator_id}`}>{t.operator_name}</Link> · a partir de {money(t.from_price_cents)}</>}
        actions={<>
          <StatusBadge status={t.status} />
          <Button asChild variant="outline"><Link to={`/admin/passeios/${t.id}/editar`}><Pencil /> Editar</Link></Button>
          {t.status === 'published' && <Button asChild variant="outline"><Link to={`/pt/passeios/${t.slug}`} target="_blank"><ExternalLink /> Ver no site</Link></Button>}
        </>} />

      {!!t.problems?.length && <p className="mb-3 flex items-center gap-1 text-sm text-amber-700"><AlertTriangle className="size-4" /> Falta: {t.problems.map(problemLabel).join(', ')}</p>}
      {!!t.contact_flags?.length && (
        <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">
          <p className="font-semibold">Possíveis contatos nos textos públicos (desintermediação)</p>
          <ul className="list-disc pl-5">{t.contact_flags.map((f, i) => <li key={i}><code>{f.field}</code>: “{f.match}”</li>)}</ul>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <article className="space-y-4 rounded-xl border bg-card p-5">
          <div className="grid grid-cols-3 gap-2">{t.photos.map((p) => <Photo key={p.id} src={p.url} alt={p.alt} className="aspect-[3/2] w-full rounded-md" />)}</div>
          <h2 className="text-lg font-semibold">{pt?.title}</h2>
          <p className="text-sm text-muted-foreground">{pt?.summary}</p>
          <p className="whitespace-pre-line text-sm">{pt?.description}</p>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Região pública</dt><dd>{t.public_area_label}</dd>
            <dt className="text-muted-foreground">Ponto exato (privado)</dt><dd>{t.meeting_point_address}</dd>
            <dt className="text-muted-foreground">Política</dt><dd>{t.cancellation_policy}</dd>
            <dt className="text-muted-foreground">Agenda</dt><dd>{t.schedules.map((s) => s.start_time).join(', ') || '—'}</dd>
            <dt className="text-muted-foreground">Idiomas</dt><dd>{t.translations.filter((x) => x.title).map((x) => x.locale).join(', ')}</dd>
          </dl>
        </article>
        <aside className="space-y-3 rounded-xl border bg-card p-4">
          <h2 className="font-semibold">Análise</h2>
          <textarea aria-label="Notas para a operadora" placeholder="Notas para a operadora (obrigatório ao rejeitar)" className={textareaClass} value={notes} onChange={(e) => setNotes(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            {t.status !== 'published' && <Button disabled={act.isPending} onClick={() => act.mutate('approve')}><Check /> Aprovar e publicar</Button>}
            {t.status !== 'rejected' && <Button variant="outline" disabled={act.isPending} onClick={() => act.mutate('reject')}><X /> Rejeitar</Button>}
            {t.status === 'published' && <Button variant="outline" disabled={act.isPending} onClick={() => act.mutate('pause')}><Pause /> Pausar</Button>}
          </div>
          {act.error && <p className="text-sm text-destructive">{errorMessage(act.error)}</p>}
          {t.review_notes && <p className="text-xs text-muted-foreground">Última nota: {t.review_notes}</p>}
        </aside>
      </div>
    </>
  )
}

import { ApiError } from '@/lib/api'

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const problems = (e.details?.problems as string[] | undefined) ?? []
    const fields = (e.details?.fields as { loc: string[]; msg: string }[] | undefined) ?? []
    if (problems.length) return `${e.message}: ${problems.map(problemLabel).join(', ')}`
    if (fields.length) return `${e.message}: ${fields.map((f) => `${f.loc.slice(1).join('.')} — ${f.msg}`).join('; ')}`
    return e.message
  }
  return 'Algo deu errado.'
}

const PROBLEMS: Record<string, string> = {
  missing_text_pt: 'texto em português',
  missing_text_es: 'texto em espanhol',
  missing_text_en: 'texto em inglês',
  missing_photo: 'pelo menos 1 foto',
  missing_price: 'preço vigente',
  missing_category: 'categoria',
  missing_location: 'ponto de encontro no mapa',
  missing_schedule: 'agenda (horários)',
}

export function problemLabel(p: string): string {
  return PROBLEMS[p] ?? p
}


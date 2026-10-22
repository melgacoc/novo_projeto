import type { Route } from './+types/privacy'
import { asLang } from '@/lib/i18n'

const TEXT = {
  pt: ['Privacidade', [
    'Coletamos nome, e-mail e WhatsApp para emitir sua reserva e falar com você sobre ela.',
    'Compartilhamos esses dados apenas com a operadora do passeio reservado.',
    'Pagamentos são processados pelo meio de pagamento; não guardamos dados de cartão.',
    'Você pode pedir a exclusão da sua conta a qualquer momento; registros financeiros são mantidos pelo prazo legal.',
    'Rascunho para validação jurídica (LGPD).',
  ]],
  es: ['Privacidad', [
    'Recopilamos nombre, correo y WhatsApp para emitir tu reserva y contactarte sobre ella.',
    'Compartimos estos datos solo con el operador del paseo reservado.',
    'Los pagos los procesa el medio de pago; no guardamos datos de tarjeta.',
    'Puedes pedir la eliminación de tu cuenta en cualquier momento; los registros financieros se guardan por el plazo legal.',
    'Borrador para validación jurídica (LGPD).',
  ]],
  en: ['Privacy', [
    'We collect your name, email and WhatsApp to issue your booking and contact you about it.',
    'We share this data only with the operator of the booked tour.',
    'Payments are processed by the payment provider; we do not store card data.',
    'You can request account deletion at any time; financial records are kept for the legal period.',
    'Draft pending legal review (LGPD).',
  ]],
} as const

export function meta({ params }: Route.MetaArgs) {
  return [{ title: TEXT[asLang(params.lang)][0] }]
}

export default function Privacy({ params }: Route.ComponentProps) {
  const [title, items] = TEXT[asLang(params.lang)]
  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
      <ul className="list-disc space-y-3 pl-5">{items.map((p) => <li key={p}>{p}</li>)}</ul>
    </div>
  )
}

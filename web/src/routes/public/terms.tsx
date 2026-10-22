import type { Route } from './+types/terms'
import { asLang } from '@/lib/i18n'

const TEXT = {
  pt: ['Termos de uso', [
    'A plataforma conecta turistas a operadoras de passeios. Cada passeio é executado pela operadora indicada no voucher.',
    'O pagamento é feito na plataforma, pelo valor total. O voucher com o ponto de encontro é enviado depois da confirmação.',
    'Cancelamento pelo turista segue a política do passeio (flexível: reembolso integral até 24 h antes; moderada: até 48 h; rígida: sem reembolso).',
    'Se o passeio for cancelado pela operadora ou por condições do tempo, o reembolso é integral.',
    'É proibido combinar pagamento por fora da plataforma para reservas feitas aqui.',
    'Rascunho para validação jurídica.',
  ]],
  es: ['Términos de uso', [
    'La plataforma conecta a turistas con operadores de paseos. Cada paseo lo realiza el operador indicado en el voucher.',
    'El pago se hace en la plataforma, por el valor total. El voucher con el punto de encuentro se envía tras la confirmación.',
    'La cancelación por el turista sigue la política del paseo (flexible: reembolso total hasta 24 h antes; moderada: hasta 48 h; estricta: sin reembolso).',
    'Si el paseo es cancelado por el operador o por el clima, el reembolso es total.',
    'Está prohibido acordar pagos fuera de la plataforma para reservas hechas aquí.',
    'Borrador para validación jurídica.',
  ]],
  en: ['Terms of use', [
    'The platform connects travelers with tour operators. Each tour is run by the operator named on the voucher.',
    'Payment is made on the platform, in full. The voucher with the meeting point is sent after confirmation.',
    'Cancellations by the traveler follow the tour policy (flexible: full refund up to 24 h before; moderate: up to 48 h; strict: non-refundable).',
    'If the operator or the weather cancels the tour, you get a full refund.',
    'Arranging payment outside the platform for bookings made here is not allowed.',
    'Draft pending legal review.',
  ]],
} as const

export function meta({ params }: Route.MetaArgs) {
  return [{ title: TEXT[asLang(params.lang)][0] }]
}

export default function Terms({ params }: Route.ComponentProps) {
  const [title, items] = TEXT[asLang(params.lang)]
  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
      <ol className="list-decimal space-y-3 pl-5">{items.map((p) => <li key={p}>{p}</li>)}</ol>
    </div>
  )
}

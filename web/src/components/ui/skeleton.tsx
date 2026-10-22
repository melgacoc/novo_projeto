import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'
import { TableCell, TableRow } from '@/components/ui/table'

/**
 * Bloco cinza pulsante que ocupa o lugar do conteúdo enquanto ele carrega.
 * Decorativo (aria-hidden): quem usa deve anunciar o carregamento por
 * `aria-busy`/`role="status"` ou por um texto `sr-only`.
 */
function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden
      className={cn('animate-pulse rounded-md bg-muted motion-reduce:animate-none', className)}
      {...props}
    />
  )
}

// larguras variadas para parecer texto de verdade (e não uma grade)
const WIDTHS = ['w-3/4', 'w-1/2', 'w-2/3', 'w-5/6', 'w-1/3']

/**
 * Linhas de tabela de carregamento. Substitui a linha "Carregando..." do
 * `<TableBody>`: mantém as colunas e a altura da tabela, então nada "pula"
 * quando os dados chegam. `label` é lido por leitores de tela.
 */
function TableSkeletonRows({ columns, rows = 5, label }: { columns: number; rows?: number; label: string }) {
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <TableRow key={r} aria-busy>
          {Array.from({ length: columns }, (_, c) => (
            <TableCell key={c}>
              <Skeleton className={cn('h-4', WIDTHS[(r + c) % WIDTHS.length])} />
              {r === 0 && c === 0 && <span className="sr-only">{label}</span>}
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}

/** Lista simples (linha do tempo, feed): barras de largura variável. */
function ListSkeleton({ rows = 4, label }: { rows?: number; label: string }) {
  return (
    <div role="status" className="space-y-3">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="space-y-1.5">
          <Skeleton className={cn('h-4', WIDTHS[i % WIDTHS.length])} />
          <Skeleton className="h-3 w-1/4" />
        </div>
      ))}
    </div>
  )
}

/** Painel de detalhe (dialog): título, campos em grade e um bloco maior. */
function DetailSkeleton({ label }: { label: string }) {
  return (
    <div role="status" className="space-y-4 py-2">
      <span className="sr-only">{label}</span>
      <Skeleton className="h-6 w-1/2" />
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="space-y-1.5">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-5 w-3/4" />
          </div>
        ))}
      </div>
      <Skeleton className="h-24 w-full" />
    </div>
  )
}

/** Cartões de totais (ex.: 3 cartões acima de uma tabela). */
function CardsSkeleton({ count = 3, label }: { count?: number; label: string }) {
  return (
    <div role="status" className="grid gap-3 sm:grid-cols-3">
      <span className="sr-only">{label}</span>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="space-y-2 rounded-lg border p-3">
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      ))}
    </div>
  )
}

export { Skeleton, TableSkeletonRows, ListSkeleton, DetailSkeleton, CardsSkeleton }

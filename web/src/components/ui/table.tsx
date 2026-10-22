import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * No celular (< 640px) cada linha vira um cartão "rótulo: valor" (ver
 * `.responsive-table` em index.css). Os rótulos saem do cabeçalho da própria
 * tabela e são aplicados nas células por aqui, então as telas não precisam
 * repetir o nome da coluna em cada célula.
 */
const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement>
>(({ className, ...props }, ref) => {
  const inner = React.useRef<HTMLTableElement>(null)
  React.useImperativeHandle(ref, () => inner.current as HTMLTableElement)

  React.useEffect(() => {
    const table = inner.current
    if (!table) return
    const applyLabels = () => {
      const heads = Array.from(table.querySelectorAll("thead th")).map(
        (th) => th.textContent?.trim() ?? ""
      )
      table.querySelectorAll("tbody tr").forEach((row) => {
        let column = 0
        Array.from(row.children).forEach((cell) => {
          const span = (cell as HTMLTableCellElement).colSpan || 1
          // linhas de "carregando/vazio" ocupam todas as colunas: sem rótulo
          if (span === 1) cell.setAttribute("data-label", heads[column] ?? "")
          else cell.removeAttribute("data-label")
          column += span
        })
      })
    }
    applyLabels()
    const observer = new MutationObserver(applyLabels)
    observer.observe(table, { childList: true, subtree: true, characterData: true })
    return () => observer.disconnect()
  }, [])

  return (
    <div className="relative w-full overflow-auto">
      <table
        ref={inner}
        className={cn("responsive-table w-full caption-bottom text-sm", className)}
        {...props}
      />
    </div>
  )
})
Table.displayName = "Table"

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
))
TableHeader.displayName = "TableHeader"

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn("[&_tr:last-child]:border-0", className)}
    {...props}
  />
))
TableBody.displayName = "TableBody"

const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={cn(
      "border-t bg-muted/50 font-medium [&>tr]:last:border-b-0",
      className
    )}
    {...props}
  />
))
TableFooter.displayName = "TableFooter"

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
      className
    )}
    {...props}
  />
))
TableRow.displayName = "TableRow"

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "h-10 px-2 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
      className
    )}
    {...props}
  />
))
TableHead.displayName = "TableHead"

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      "p-2 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
      className
    )}
    {...props}
  />
))
TableCell.displayName = "TableCell"

const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn("mt-4 text-sm text-muted-foreground", className)}
    {...props}
  />
))
TableCaption.displayName = "TableCaption"

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}

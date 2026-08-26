import { flexRender, type RowData } from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { useRef, type KeyboardEvent } from "react"

import { useDataTableContext } from "@/components/data-table/data-table-context"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

const VIRTUALIZATION_THRESHOLD = 50
const ESTIMATED_ROW_HEIGHT = 44
const OVERSCAN = 10

type DataTableContentProps = {
  children?: React.ReactNode
  className?: string
}

export function DataTableContent<TData extends RowData>({
  children,
  className,
}: DataTableContentProps) {
  const { table, onRowClick } = useDataTableContext<TData>()
  const scrollRef = useRef<HTMLDivElement>(null)
  const rows = table.getRowModel().rows
  const hasRows = rows.length > 0
  const shouldVirtualize = rows.length > VIRTUALIZATION_THRESHOLD

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    estimateSize: () => ESTIMATED_ROW_HEIGHT,
    getScrollElement: () => scrollRef.current,
    overscan: OVERSCAN,
    enabled: shouldVirtualize,
  })

  const renderRow = (row: (typeof rows)[number]) => {
    const clickable = !!onRowClick
    const onActivate = () => {
      onRowClick?.(row.original)
    }

    return (
      <TableRow
        key={row.id}
        data-state={row.getIsSelected() ? "selected" : undefined}
        role={clickable ? "button" : undefined}
        tabIndex={clickable ? 0 : undefined}
        className={cn(clickable && "cursor-pointer")}
        onClick={clickable ? onActivate : undefined}
        onKeyDown={
          clickable
            ? (event: KeyboardEvent<HTMLTableRowElement>) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault()
                  onActivate()
                }
              }
            : undefined
        }
      >
        {row.getVisibleCells().map((cell) => (
          <TableCell key={cell.id}>
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </TableCell>
        ))}
      </TableRow>
    )
  }

  const virtualItems = rowVirtualizer.getVirtualItems()
  const paddingTop = shouldVirtualize && virtualItems.length > 0 ? virtualItems[0].start : 0
  const lastItem = virtualItems.at(-1)
  const paddingBottom =
    shouldVirtualize && lastItem
      ? rowVirtualizer.getTotalSize() - (lastItem.start + lastItem.size)
      : 0

  return (
    <div className={cn("rounded-md border", className)}>
      <div
        ref={scrollRef}
        className={cn(shouldVirtualize && "max-h-[70vh] overflow-y-auto")}
      >
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-background">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {hasRows ? (
              shouldVirtualize ? (
                <>
                  {paddingTop > 0 && (
                    <tr>
                      <td style={{ height: paddingTop }} />
                    </tr>
                  )}
                  {virtualItems.map((virtualItem) =>
                    renderRow(rows[virtualItem.index])
                  )}
                  {paddingBottom > 0 && (
                    <tr>
                      <td style={{ height: paddingBottom }} />
                    </tr>
                  )}
                </>
              ) : (
                rows.map(renderRow)
              )
            ) : (
              children
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

import {
  flexRender,
  type Row,
  type RowData,
} from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { memo, useRef, type KeyboardEvent } from "react"

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
const ESTIMATED_ROW_HEIGHT = 41
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
  const rows: Row<TData>[] = table.getRowModel().rows
  const hasRows = rows.length > 0
  const shouldVirtualize = rows.length > VIRTUALIZATION_THRESHOLD

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    estimateSize: () => ESTIMATED_ROW_HEIGHT,
    getScrollElement: () => scrollRef.current,
    overscan: OVERSCAN,
    enabled: shouldVirtualize,
  })

  // Memoization key for MemoizedDataTableRow — changes only when columns change
  const visibleColumnIds = table
    .getVisibleLeafColumns()
    .map((column) => column.id)
    .join(",")

  const virtualItems = rowVirtualizer.getVirtualItems()
  const paddingTop =
    shouldVirtualize && virtualItems.length > 0 ? virtualItems[0].start : 0
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
            {!hasRows ? (
              children
            ) : shouldVirtualize ? (
              <>
                {paddingTop > 0 && (
                  <tr aria-hidden="true">
                    <td style={{ height: paddingTop }} />
                  </tr>
                )}
                {virtualItems.map((virtualItem) => (
                  <MemoizedDataTableRow
                    key={rows[virtualItem.index].id}
                    row={rows[virtualItem.index]}
                    selected={rows[virtualItem.index].getIsSelected()}
                    visibleColumnIds={visibleColumnIds}
                    onRowClick={onRowClick}
                  />
                ))}
                {paddingBottom > 0 && (
                  <tr aria-hidden="true">
                    <td style={{ height: paddingBottom }} />
                  </tr>
                )}
              </>
            ) : (
              rows.map((row) => (
                <MemoizedDataTableRow
                  key={row.id}
                  row={row}
                  selected={row.getIsSelected()}
                  visibleColumnIds={visibleColumnIds}
                  onRowClick={onRowClick}
                />
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function DataTableRow<TData extends RowData>({
  row,
  selected,
  onRowClick,
}: {
  row: Row<TData>
  selected: boolean
  visibleColumnIds: string
  onRowClick?: (row: TData) => void
}) {
  const clickable = !!onRowClick
  const onActivate = () => {
    onRowClick?.(row.original)
  }

  return (
    <TableRow
      data-state={selected ? "selected" : undefined}
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

const MemoizedDataTableRow = memo(
  DataTableRow,
  (prev, next) =>
    prev.row.id === next.row.id &&
    prev.selected === next.selected &&
    prev.visibleColumnIds === next.visibleColumnIds &&
    prev.onRowClick === next.onRowClick
) as typeof DataTableRow

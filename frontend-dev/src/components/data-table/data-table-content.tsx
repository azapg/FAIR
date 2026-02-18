import { flexRender, type RowData } from "@tanstack/react-table"
import type { KeyboardEvent } from "react"

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

type DataTableContentProps = {
  children?: React.ReactNode
  className?: string
}

export function DataTableContent<TData extends RowData>({
  children,
  className,
}: DataTableContentProps) {
  const { table, onRowClick } = useDataTableContext<TData>()
  const rows = table.getRowModel().rows
  const hasRows = rows.length > 0

  return (
    <div className={cn("rounded-md border", className)}>
      <Table>
        <TableHeader>
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
          {hasRows
            ? rows.map((row) => {
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
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                )
              })
            : children}
        </TableBody>
      </Table>
    </div>
  )
}


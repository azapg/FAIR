import type { RowData } from "@tanstack/react-table"

import { useDataTableContext } from "@/components/data-table/data-table-context"
import { Empty } from "@/components/ui/empty"
import { TableCell, TableRow } from "@/components/ui/table"

type DataTableEmptyProps = {
  children?: React.ReactNode
}

export function DataTableEmpty<TData extends RowData>({
  children,
}: DataTableEmptyProps) {
  const { table } = useDataTableContext<TData>()
  const columnCount = table.getVisibleLeafColumns().length

  return (
    <TableRow className="hover:bg-background">
      <TableCell colSpan={columnCount}>
        {children ?? <Empty />}
      </TableCell>
    </TableRow>
  )
}


import {
  type ColumnDef,
  type ColumnFiltersState,
  type OnChangeFn,
  type RowData,
  type RowSelectionState,
  type SortingState,
  type TableMeta,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { useState } from "react"

import { DataTableProvider } from "@/components/data-table/data-table-context"

type DataTableState = {
  sorting?: SortingState
  columnFilters?: ColumnFiltersState
  rowSelection?: RowSelectionState
}

type DataTableProps<TData, TValue> = {
  data: TData[]
  columns: ColumnDef<TData, TValue>[]
  filterKey?: string
  onRowClick?: (row: TData) => void
  children: React.ReactNode
  enableRowSelection?: boolean
  state?: DataTableState
  onRowSelectionChange?: OnChangeFn<RowSelectionState>
  meta?: TableMeta<TData>
}

export function DataTable<TData extends RowData, TValue>({
  data,
  columns,
  filterKey,
  onRowClick,
  children,
  enableRowSelection = false,
  state,
  onRowSelectionChange,
  meta,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onRowSelectionChange,
    enableRowSelection,
    state: {
      sorting: state?.sorting ?? sorting,
      columnFilters: state?.columnFilters ?? columnFilters,
      rowSelection: state?.rowSelection ?? {},
    },
    meta,
  })

  return (
    <DataTableProvider value={{ table, filterKey, onRowClick }}>
      {children}
    </DataTableProvider>
  )
}

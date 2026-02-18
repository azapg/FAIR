import {
  type ColumnDef,
  type ColumnFiltersState,
  type OnChangeFn,
  type PaginationState,
  type RowData,
  type RowSelectionState,
  type SortingState,
  type TableMeta,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { useState } from "react"

import { DataTableProvider } from "@/components/data-table/data-table-context"

type DataTableState = {
  sorting?: SortingState
  columnFilters?: ColumnFiltersState
  pagination?: PaginationState
  rowSelection?: RowSelectionState
}

type DataTableProps<TData, TValue> = {
  data: TData[]
  columns: ColumnDef<TData, TValue>[]
  filterKey?: string
  onRowClick?: (row: TData) => void
  children: React.ReactNode
  enableRowSelection?: boolean
  enablePagination?: boolean
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
  enablePagination = false,
  state,
  onRowSelectionChange,
  meta,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: enablePagination ? setPagination : undefined,
    onRowSelectionChange,
    enableRowSelection,
    state: {
      sorting: state?.sorting ?? sorting,
      columnFilters: state?.columnFilters ?? columnFilters,
      pagination:
        enablePagination
          ? (state?.pagination ?? pagination)
          : { pageIndex: 0, pageSize: data.length || 1 },
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

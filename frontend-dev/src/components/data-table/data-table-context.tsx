import { createContext, useContext } from "react"
import type { RowData, Table } from "@tanstack/react-table"

export type DataTableContextValue<TData extends RowData> = {
  table: Table<TData>
  filterKey?: string
  onRowClick?: (row: TData) => void
}

const DataTableContext = createContext<DataTableContextValue<RowData> | null>(
  null
)

export function DataTableProvider<TData extends RowData>({
  value,
  children,
}: {
  value: DataTableContextValue<TData>
  children: React.ReactNode
}) {
  return (
    <DataTableContext.Provider value={value as DataTableContextValue<RowData>}>
      {children}
    </DataTableContext.Provider>
  )
}

export function useDataTableContext<TData extends RowData>() {
  const context = useContext(DataTableContext)
  if (!context) {
    throw new Error("DataTable compound components must be used within DataTable")
  }
  return context as DataTableContextValue<TData>
}


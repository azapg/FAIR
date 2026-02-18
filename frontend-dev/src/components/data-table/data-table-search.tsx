import type { RowData } from "@tanstack/react-table"
import { useTranslation } from "react-i18next"

import { useDataTableContext } from "@/components/data-table/data-table-context"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

type DataTableSearchProps = {
  placeholder?: string
  className?: string
}

export function DataTableSearch<TData extends RowData>({
  placeholder,
  className,
}: DataTableSearchProps) {
  const { t } = useTranslation()
  const { table, filterKey } = useDataTableContext<TData>()

  if (!filterKey) {
    return null
  }

  const column = table.getColumn(filterKey)
  const value = String(column?.getFilterValue() ?? "")

  return (
    <Input
      value={value}
      onChange={(event) => column?.setFilterValue(event.target.value)}
      placeholder={placeholder ?? t("common.search")}
      className={cn("w-full md:max-w-sm", className)}
    />
  )
}


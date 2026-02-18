import type { RowData } from "@tanstack/react-table"
import { useTranslation } from "react-i18next"

import { useDataTableContext } from "@/components/data-table/data-table-context"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

type DataTablePaginationProps = {
  className?: string
}

export function DataTablePagination<TData extends RowData>({
  className,
}: DataTablePaginationProps) {
  const { t } = useTranslation()
  const { table } = useDataTableContext<TData>()

  return (
    <div className={cn("flex flex-col gap-3 py-2 md:flex-row md:items-center md:justify-between", className)}>
      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">{t("common.rowsPerPage")}</span>
        <Select
          value={`${table.getState().pagination.pageSize}`}
          onValueChange={(value) => table.setPageSize(Number(value))}
        >
          <SelectTrigger size="sm" className="h-8 w-[76px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent side="top">
            {PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={`${size}`}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center justify-between gap-2 md:justify-end">
        <div className="text-sm text-muted-foreground">
          {t("common.page")} {table.getState().pagination.pageIndex + 1} {t("common.of")}{" "}
          {Math.max(1, table.getPageCount())}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          >
            {t("common.first")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {t("common.previous")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {t("common.next")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          >
            {t("common.last")}
          </Button>
        </div>
      </div>
    </div>
  )
}


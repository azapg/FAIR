import { ColumnDef } from "@tanstack/react-table"
import { TableProperties } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Assignment } from "@/hooks/use-assignments"

interface DataTableProps {
  columns: ColumnDef<Assignment>[]
  data: Assignment[]
}

export function AssignmentsTable({ columns, data }: DataTableProps) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  return (
    <DataTable
      data={data}
      columns={columns}
      filterKey="title"
      onRowClick={(row) => {
        if (row.id) {
          navigate(row.id, { relative: "path" })
        }
      }}
    >
      <div className="py-4">
        <DataTableSearch />
      </div>

      <DataTableContent>
        <DataTableEmpty>
          <Empty className="w-full items-start text-left lg:items-center lg:text-center">
            <EmptyHeader className="items-start text-left lg:items-center lg:text-center">
              <EmptyMedia variant="icon">
                <TableProperties />
              </EmptyMedia>
              <EmptyTitle>{t("assignments.title")}</EmptyTitle>
              <EmptyDescription>{t("common.noResults")}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </DataTableEmpty>
      </DataTableContent>
    </DataTable>
  )
}

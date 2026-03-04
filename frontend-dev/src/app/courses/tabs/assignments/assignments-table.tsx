import { ColumnDef } from "@tanstack/react-table"
import { TableProperties, ArrowUpRightIcon } from "lucide-react"
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
  EmptyContent,
} from "@/components/ui/empty"
import { Button } from "@/components/ui/button"
import { Assignment } from "@/hooks/use-assignments"
import { DOCS_BASE_URL } from "@/lib/constants"

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
            <EmptyContent>
              <Button
                variant="link"
                asChild
                className="text-muted-foreground p-0 h-auto"
                size="sm"
              >
                <a
                  href={`${DOCS_BASE_URL}/en/platform/assignments/`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("common.learnMore")} <ArrowUpRightIcon className="ml-1 h-4 w-4" />
                </a>
              </Button>
            </EmptyContent>
          </Empty>
        </DataTableEmpty>
      </DataTableContent>
    </DataTable>
  )
}

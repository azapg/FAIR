import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  onCreateSubmission?: () => void;
}

import { TableProperties, ArrowUpRightIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { useTranslation } from "react-i18next";

export function EmptyTableState({
  onCreateSubmission,
}: {
  onCreateSubmission?: () => void;
}) {
  const { t } = useTranslation();

  return (
    <Empty className="w-full items-start text-center lg:items-center lg:text-center">
      <EmptyHeader className="items-start text-start lg:items-center lg:text-center">
        <EmptyMedia variant="icon">
          <TableProperties />
        </EmptyMedia>
        <EmptyTitle>{t("submissions.noSubmissons")}</EmptyTitle>
        <EmptyDescription>
          {t("submissions.noSubmissonsDescription")}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="items-start lg:items-center">
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCreateSubmission}>
            {t("submissions.addSubmissions")}
          </Button>
          <Button
            variant="link"
            asChild
            className="text-muted-foreground"
            size="sm"
          >
            <a href="#">
              {t("common.learnMore")} <ArrowUpRightIcon />
            </a>
          </Button>
        </div>
      </EmptyContent>
    </Empty>
  );
}

export function SubmissionsTable<TData, TValue>({
  columns,
  data,
  onCreateSubmission,
}: DataTableProps<TData, TValue>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const rows = table.getRowModel().rows;
  const hasRows = rows.length > 0;

  return (
    <div className={"w-full rounded-md border"}>
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {hasRows ? (
            rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow className="hover:bg-background">
              <TableCell colSpan={columns.length}>
                <EmptyTableState onCreateSubmission={onCreateSubmission} />
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
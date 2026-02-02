import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { TableProperties, ArrowUpRightIcon } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
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
import { Submission, SubmissionStatus } from "@/hooks/use-submissions";

interface DataTableProps {
  columns: ColumnDef<Submission>[];
  data: Submission[];
  onCreateSubmission?: () => void;
}

const SUBMISSION_VIEWS: Array<{
  id: string;
  labelKey: string;
  statuses: SubmissionStatus[];
}> = [
  {
    id: "inbox",
    labelKey: "submissions.views.inbox",
    statuses: ["pending", "submitted"],
  },
  {
    id: "active",
    labelKey: "submissions.views.active",
    statuses: [
      "transcribing",
      "transcribed",
      "grading",
      "graded",
      "processing",
      "needs_review",
      "failure",
    ],
  },
  {
    id: "finalized",
    labelKey: "submissions.views.finalized",
    statuses: ["returned", "excused"],
  },
];

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

export function SubmissionsTable({
  columns,
  data,
  onCreateSubmission,
}: DataTableProps) {
  const { t } = useTranslation();
  const [activeView, setActiveView] = useState(SUBMISSION_VIEWS[0].id);
  const [searchQuery, setSearchQuery] = useState("");
  const [rowSelection, setRowSelection] = useState({});

  const filteredData = useMemo(() => {
    const view = SUBMISSION_VIEWS.find((item) => item.id === activeView);
    const viewStatuses = view?.statuses ?? [];
    const normalizedQuery = searchQuery.trim().toLowerCase();

    return data.filter((submission) => {
      const matchesView = viewStatuses.includes(submission.status);
      if (!matchesView) return false;
      if (!normalizedQuery) return true;

      const searchTargets = [
        submission.submitter?.name ?? "",
        submission.submitter?.email ?? "",
        submission.status,
      ]
        .join(" ")
        .toLowerCase();

      return searchTargets.includes(normalizedQuery);
    });
  }, [activeView, data, searchQuery]);

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    state: {
      rowSelection,
    },
  });

  const rows = table.getRowModel().rows;
  const hasRows = rows.length > 0;
  const selectedRowsCount = table.getSelectedRowModel().rows.length;

  return (
    <div className="w-full space-y-4">
      <Tabs value={activeView} onValueChange={setActiveView}>
        <TabsList className="w-full justify-start">
          {SUBMISSION_VIEWS.map((view) => (
            <TabsTrigger key={view.id} value={view.id}>
              {t(view.labelKey)}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="w-full md:max-w-sm">
          <Input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder={t("submissions.searchPlaceholder")}
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground md:justify-end">
          <span>
            {t("submissions.selectedRows", {
              selected: selectedRowsCount,
              total: rows.length,
            })}
          </span>
          <Button
            variant="secondary"
            disabled={selectedRowsCount === 0}
          >
            {t("submissions.returnAction")}
          </Button>
        </div>
      </div>

      <div className="w-full rounded-md border">
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
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
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
    </div>
  );
}

import { type ColumnDef, type RowSelectionState } from "@tanstack/react-table";
import { TableProperties, ArrowUpRightIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTablePagination,
  DataTableSearch,
  useDataTableContext,
} from "@/components/data-table";
import {
  Submission,
  SubmissionStatus,
  useReturnSubmissions,
} from "@/hooks/use-submissions";
import { SubmissionSheet } from "@/app/assignment/components/submissions/submission-sheet";

interface DataTableProps {
  columns: ColumnDef<Submission>[];
  data: Submission[];
  onCreateSubmission?: () => void;
  canManage?: boolean;
}

const SUBMISSION_VIEWS: Array<{
  id: string;
  labelKey: string;
  statuses: SubmissionStatus[];
}> = [
  {
    id: "all",
    labelKey: "submissions.views.all",
    statuses: [],
  },
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
          {onCreateSubmission && (
            <Button variant="outline" onClick={onCreateSubmission}>
              {t("submissions.addSubmissions")}
            </Button>
          )}
        </div>
      </EmptyContent>
    </Empty>
  );
}

function SubmissionsToolbar({
  returnSubmissions,
}: {
  returnSubmissions: ReturnType<typeof useReturnSubmissions>;
}) {
  const { t } = useTranslation();
  const { table } = useDataTableContext<Submission>();

  const selectedRowsCount = table.getSelectedRowModel().rows.length;
  const totalRowsCount = table.getFilteredRowModel().rows.length;

  const returnableSubmissionIds = table
    .getSelectedRowModel()
    .rows.map((row) => row.original)
    .filter(
      (submission) =>
        submission.status !== "returned" &&
        (submission.draftScore != null || submission.draftFeedback != null),
    )
    .map((submission) => submission.id);

  const hasReturnableSelection = returnableSubmissionIds.length > 0;

  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div className="w-full md:max-w-sm">
        <DataTableSearch placeholder={t("submissions.searchPlaceholder")} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground md:justify-end">
        <span>
          {t("submissions.selectedRows", {
            selected: selectedRowsCount,
            total: totalRowsCount,
          })}
        </span>
        <Button
          variant="secondary"
          disabled={!hasReturnableSelection || returnSubmissions.isPending}
          onClick={() => returnSubmissions.mutate(returnableSubmissionIds)}
        >
          {t("submissions.returnAction")}
        </Button>
      </div>
    </div>
  );
}

export function SubmissionsTable({
  columns,
  data,
  onCreateSubmission,
  canManage = true,
}: DataTableProps) {
  const { t } = useTranslation();
  const [activeView, setActiveView] = useState(SUBMISSION_VIEWS[0].id);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [selectedSubmissionId, setSelectedSubmissionId] =
    useState<string | null>(null);
  const [focusOn, setFocusOn] = useState<"feedback" | null>(null);
  const returnSubmissions = useReturnSubmissions();

  const selectedSubmission = useMemo(() => {
    return data.find((s) => s.id === selectedSubmissionId) || null;
  }, [data, selectedSubmissionId]);

  const filteredData = useMemo(() => {
    const view = SUBMISSION_VIEWS.find((item) => item.id === activeView);
    const viewStatuses = view?.statuses ?? [];

    return data.filter((submission) => {
      return view?.id === "all" ? true : viewStatuses.includes(submission.status);
    });
  }, [activeView, data]);

  const onFeedbackClick = (submission: Submission) => {
    setSelectedSubmissionId(submission.id);
    setFocusOn("feedback");
  };

  return (
    <div className="space-y-4">
      <Tabs value={activeView} onValueChange={setActiveView}>
        <TabsList>
          {SUBMISSION_VIEWS.map((view) => (
            <TabsTrigger key={view.id} value={view.id}>
              {t(view.labelKey)}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <DataTable
        data={filteredData}
        columns={columns}
        filterKey="submitter.name"
        enableRowSelection={canManage}
        enablePagination
        onRowSelectionChange={setRowSelection}
        state={{ rowSelection }}
        meta={{ onFeedbackClick }}
        onRowClick={(submission) => {
          setSelectedSubmissionId(submission.id);
          setFocusOn(null);
        }}
      >
        <SubmissionsToolbar
          returnSubmissions={returnSubmissions}
        />

        <DataTableContent>
          <DataTableEmpty>
            <EmptyTableState
              onCreateSubmission={canManage ? onCreateSubmission : undefined}
            />
          </DataTableEmpty>
        </DataTableContent>

        <DataTablePagination />
      </DataTable>

      <SubmissionSheet
        submission={selectedSubmission}
        open={!!selectedSubmission}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedSubmissionId(null);
            setFocusOn(null);
          }
        }}
        focusOn={focusOn}
      />
    </div>
  );
}

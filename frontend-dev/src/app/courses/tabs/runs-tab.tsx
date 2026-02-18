import { ColumnDef } from "@tanstack/react-table";
import { ReactNode, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Circle,
  CircleAlert,
  CircleCheck,
  CircleX,
  Loader,
  SquircleDashed,
} from "lucide-react";

import { DataTable, DataTableContent, DataTableEmpty } from "@/components/data-table";
import { useWorkflowRuns } from "@/hooks/use-workflow-runs";
import { useWorkflows } from "@/hooks/use-workflows";
import { WorkflowRun, WorkflowRunStatus } from "@/store/workflows-store";

const defaultSize = 14;

const STATUS_ICONS: Record<WorkflowRunStatus, ReactNode> = {
  pending: <SquircleDashed size={defaultSize} />,
  running: (
    <Loader
      className="animate-spin [animation-duration:4.0s]"
      size={defaultSize}
    />
  ),
  success: <CircleCheck size={defaultSize} />,
  failure: <CircleAlert size={defaultSize} />,
  cancelled: <CircleX size={defaultSize} />,
};

const STATUS_COLORS: Record<WorkflowRunStatus, string> = {
  pending: "gray-500",
  running: "yellow-500",
  success: "blue-500",
  failure: "red-500",
  cancelled: "gray-500",
};

interface WorkflowRunStatusLabelProps {
  status: WorkflowRunStatus;
}

const WorkflowRunStatusLabel = ({ status }: WorkflowRunStatusLabelProps) => {
  const { t } = useTranslation();

  const color = STATUS_COLORS[status] ?? "gray-500";
  const icon = STATUS_ICONS[status] ?? <Circle size={defaultSize} />;

  const labelKey = `status.${status}`;
  const label = t([labelKey, "status.unknown"]);

  return (
    <span
      className={`inline-flex items-center justify-center rounded-md border gap-1 pl-1 pr-1 text-sm
        text-${color} bg-${color}/10`}
    >
      {icon}
      <span className="text-foreground">{label}</span>
    </span>
  );
};

function formatDuration(start?: string | null, end?: string | null) {
  if (!start || !end) return "—";
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  const diff = Math.max(0, e - s);
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
}

export function RunsTab({ courseId }: { courseId?: string }) {
  const { t } = useTranslation();
  const {
    data: runs,
    isLoading: runsLoading,
    isError: runsError,
  } = useWorkflowRuns({ courseId: courseId ?? "" });
  const { workflows } = useWorkflows();

  const workflowNames = useMemo(() => {
    const map = new Map<string, string>();
    workflows?.forEach((w) => map.set(w.id, w.name));
    return map;
  }, [workflows]);

  const columns = useMemo<ColumnDef<WorkflowRun>[]>(
    () => [
      {
        id: "workflow",
        header: t("runs.workflow"),
        cell: ({ row }) => (
          <span className="font-medium">
            {workflowNames.get(row.original.workflowId) ?? row.original.workflowId}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: t("runs.status"),
        cell: ({ row }) => <WorkflowRunStatusLabel status={row.original.status} />,
      },
      {
        id: "submissions",
        header: t("runs.submissions"),
        cell: ({ row }) => row.original.submissions?.length || 0,
      },
      {
        accessorKey: "startedAt",
        header: t("runs.startedAt"),
        cell: ({ row }) =>
          row.original.startedAt ? new Date(row.original.startedAt).toLocaleString() : "—",
      },
      {
        id: "duration",
        header: t("runs.duration"),
        cell: ({ row }) => formatDuration(row.original.startedAt, row.original.finishedAt),
      },
      {
        id: "runBy",
        header: () => <div className="text-right">{t("runs.runBy")}</div>,
        cell: ({ row }) => (
          <div className="text-right">
            {row.original.runner?.name || t("submissions.timelineEvents.actor.system")}
          </div>
        ),
      },
    ],
    [t, workflowNames],
  );

  if (!courseId) {
    return <div className="text-sm text-muted-foreground">{t("runs.noCourse")}</div>;
  }

  if (runsLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (runsError) {
    return <div>{t("runs.errorLoading")}</div>;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("runs.title")}</h3>
      <DataTable data={runs ?? []} columns={columns}>
        <DataTableContent>
          <DataTableEmpty>{t("runs.empty")}</DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

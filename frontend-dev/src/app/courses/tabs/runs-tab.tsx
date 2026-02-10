import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useWorkflowRuns } from "@/hooks/use-workflow-runs";
import { useWorkflows } from "@/hooks/use-workflows";

import { ReactNode } from "react";
import {
  CircleCheck,
  CircleAlert,
  Loader,
  SquircleDashed,
  CircleX,
  Circle,
} from "lucide-react";
import { WorkflowRunStatus } from "@/store/workflows-store";

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
      className={`inline-flex items-center justify-center rounded-md border pl-1 pr-1 gap-1 text-sm
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

  if (!courseId) {
    return (
      <div className="text-sm text-muted-foreground">{t("runs.noCourse")}</div>
    );
  }

  if (runsLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (runsError) {
    return <div>{t("runs.errorLoading")}</div>;
  }

  if (!runs || runs.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">{t("runs.empty")}</div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("runs.title")}</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("runs.workflow")}</TableHead>
            <TableHead>{t("runs.status")}</TableHead>
            <TableHead>{t("runs.submissions")}</TableHead>
            <TableHead>{t("runs.startedAt")}</TableHead>
            <TableHead>{t("runs.duration")}</TableHead>
            <TableHead className="text-right">{t("runs.runBy")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => {
            const workflowName =
              workflowNames.get(run.workflowId) ?? run.workflowId;
            const startedAt = run.startedAt
              ? new Date(run.startedAt).toLocaleString()
              : "—";

            return (
              <TableRow key={run.id}>
                <TableCell className="font-medium">{workflowName}</TableCell>
                <TableCell>
                  <WorkflowRunStatusLabel status={run.status} />
                </TableCell>
                <TableCell>{run.submissions?.length || 0}</TableCell>
                <TableCell>{startedAt}</TableCell>
                <TableCell>
                  {formatDuration(run.startedAt, run.finishedAt)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs">
                  {run.runBy}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

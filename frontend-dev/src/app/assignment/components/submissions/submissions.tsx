import { ColumnDef } from "@tanstack/react-table";
import {
  Ellipsis,
  History,
  Loader,
  ArrowRightLeft,
  Repeat,
  RotateCw,
  Trash,
  SquircleDashed,
  CircleCheck,
  CircleAlert,
  TriangleAlert,
  Circle,
  BlocksIcon,
} from "lucide-react";
import { ReactNode, useMemo } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useWorkflowStore, Workflow } from "@/store/workflows-store";
import { RuntimePlugin } from "@/hooks/use-plugins";
import { useWorkflows } from "@/hooks/use-workflows";
import { SubmissionStatus, Submission } from "@/hooks/use-submissions";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";

function formatShortDate(date: Date) {
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const day = date.getDate().toString().padStart(2, "0");
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  const currentYear = new Date().getFullYear();
  return currentYear === year ? `${day} ${month}` : `${day} ${month} ${year}`;
}

const defaultSize = 14;

const STATUS_ICONS: Record<string, ReactNode> = {
  pending: <SquircleDashed size={defaultSize} />,
  submitted: <Circle size={defaultSize} />,
  transcribing: (
    <Loader
      className="animate-spin [animation-duration:4.0s]"
      size={defaultSize}
    />
  ),
  transcribed: <CircleCheck size={defaultSize} />,
  grading: (
    <Loader
      className="animate-spin [animation-duration:4.0s]"
      size={defaultSize}
    />
  ),
  graded: <CircleCheck size={defaultSize} />,
  needs_review: <CircleAlert size={defaultSize} />,
  failure: <TriangleAlert size={defaultSize} />,
  processing: (
    <Loader
      className="animate-spin [animation-duration:4.0s]"
      size={defaultSize}
    />
  ),
};

const STATUS_COLORS: Record<string, string> = {
  pending: "black",
  submitted: "gray-500",
  transcribing: "yellow-500",
  transcribed: "blue-500",
  grading: "yellow-500",
  graded: "blue-500",
  needs_review: "orange-500",
  failure: "red-500",
  processing: "yellow-500",
};

interface SubmissionStatusLabelProps {
  status: SubmissionStatus | string;
}

export const SubmissionStatusLabel = ({
  status,
}: SubmissionStatusLabelProps) => {
  const { t } = useTranslation();

  const statusKey = status as keyof typeof STATUS_COLORS;
  const color = STATUS_COLORS[statusKey] ?? "gray-500";
  const icon = STATUS_ICONS[statusKey];

  // Map status to translation key
  const labelKey = `status.${status === "needs_review" ? "needsReview" : status}`;
  const label = t(labelKey);

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

interface SkeletonStatusProps {
  pulse?: boolean;
  status?: SubmissionStatus;
}

const SkeletonStatus = ({ pulse, status }: SkeletonStatusProps) => {
  const animate =
    pulse ||
    (status && ["transcribing", "grading", "processing"].includes(status));
  return (
    <div
      className={`bg-accent h-2 w-8 rounded-md ${animate ? "animate-pulse" : ""}`}
    ></div>
  );
};

// Create a hook to get translated columns
export function useSubmissionColumns(): ColumnDef<Submission>[] {
  const { t } = useTranslation();

  return useMemo(
    () => [
      {
        accessorKey: "submitter.name",
        header: t("submissions.studentNameColumn"),
        cell: (info) => info.getValue(),
      },
      {
        accessorKey: "status",
        header: t("submissions.status"),
        cell: (info) => {
          const status = info.getValue() as SubmissionStatus;
          return <SubmissionStatusLabel status={status} />;
        },
      },
      {
        accessorKey: "officialResult.score",
        header: t("submissions.grade"),
        cell: (info) => {
          const grade = info.getValue();
          return typeof grade === "number" ? (
            `${grade}/100`
          ) : (
            <SkeletonStatus status={info.cell.row.original.status} />
          );
        },
      },
      {
        accessorKey: "submittedAt",
        header: t("submissions.submissionDate"),
        cell: (info) => {
          const date = info.getValue() as Date;
          return date ? (
            formatShortDate(new Date(date))
          ) : (
            <SkeletonStatus status={info.cell.row.original.status} />
          );
        },
      },
      {
        accessorKey: "officialResult.feedback",
        header: t("submissions.feedback"),
        cell: (info) => {
          const feedback = info.getValue() as string | undefined;
          if (!feedback)
            return <SkeletonStatus status={info.cell.row.original.status} />;

          const maxLength = 50;
          const abbreviated =
            feedback.length > maxLength
              ? `${feedback.slice(0, maxLength)}...`
              : feedback;

          return (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="cursor-default truncate block max-w-xs">
                  {abbreviated}
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-sm whitespace-pre-wrap">{feedback}</p>
              </TooltipContent>
            </Tooltip>
          );
        },
      },
      {
        id: "actions",
        cell: (info) => (
          <SubmissionActionsCell submission={info.row.original} />
        ),
      },
    ],
    [t],
  );
}

// Separate component for actions to use hooks properly
function SubmissionActionsCell({ submission }: { submission: Submission }) {
  const { t } = useTranslation();
  const { workflows } = useWorkflows();
  const activeWorkflowId = useWorkflowStore((state) => state.activeWorkflowId);

  const workflow = useMemo(() => {
    if (activeWorkflowId)
      return workflows.find((w) => w.id === activeWorkflowId);
    return workflows[0];
  }, [activeWorkflowId, workflows]);

  function runPlugin(plugin?: RuntimePlugin) {
    if (!plugin) return;
    console.log(
      `Running plugin ${plugin.id}-${plugin.hash}-${plugin.version} on submission ${submission.id} with workflow ${workflow?.id} and settings`,
      plugin.settings,
    );
  }

  function runWorkflow(wf?: Workflow) {
    if (!wf) return;
    console.log(
      `Rerunning submission ${submission.id} with workflow ${wf.id}`,
      wf,
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className={"cursor-pointer"}>
        <Ellipsis size={18} />
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className={"gap-2"}>
            <BlocksIcon size={16} className={"text-muted-foreground"} />{" "}
            {t("plugins.runPlugin")}
          </DropdownMenuSubTrigger>
          <DropdownMenuPortal>
            <DropdownMenuSubContent>
              {workflow?.plugins == undefined && (
                <DropdownMenuItem disabled>
                  {t("workflow.noPlugins")}
                </DropdownMenuItem>
              )}

              {workflow &&
                workflow?.plugins &&
                workflow?.plugins?.transcriber && (
                  <>
                    <DropdownMenuItem
                      onClick={(_) => runPlugin(workflow.plugins.transcriber)}
                    >
                      {workflow.plugins.transcriber.settingsSchema.title}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}

              {workflow && workflow?.plugins && workflow?.plugins?.grader && (
                <>
                  <DropdownMenuItem
                    onClick={(_) => runPlugin(workflow.plugins.grader)}
                  >
                    {workflow.plugins.grader.settingsSchema.title}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}

              {workflow &&
                workflow?.plugins &&
                workflow?.plugins?.validator && (
                  <>
                    <DropdownMenuItem
                      onClick={(_) => workflow.plugins.validator}
                    >
                      {workflow.plugins.validator.settingsSchema.title}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
            </DropdownMenuSubContent>
          </DropdownMenuPortal>
        </DropdownMenuSub>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className={"gap-2"}>
            <ArrowRightLeft size={16} className={"text-muted-foreground"} />{" "}
            {t("actions.rerunWith")}
          </DropdownMenuSubTrigger>
          <DropdownMenuPortal>
            <DropdownMenuSubContent>
              {workflows?.map((wf) => (
                <DropdownMenuItem key={wf.id} onClick={(_) => runWorkflow(wf)}>
                  {wf.name}
                </DropdownMenuItem>
              ))}
              {workflows?.length === 0 && (
                <DropdownMenuItem disabled>
                  {t("workflow.noWorkflows")}
                </DropdownMenuItem>
              )}
            </DropdownMenuSubContent>
          </DropdownMenuPortal>
        </DropdownMenuSub>
        <DropdownMenuItem onClick={(_) => runWorkflow((workflows || [])[0])}>
          <Repeat /> {t("actions.rerun")}
        </DropdownMenuItem>
        <DropdownMenuItem>
          <History size={16} /> {t("actions.history")}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <RotateCw size={16} /> {t("actions.reset")}
        </DropdownMenuItem>
        <DropdownMenuItem variant={"destructive"}>
          <Trash size={16} /> {t("actions.remove")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

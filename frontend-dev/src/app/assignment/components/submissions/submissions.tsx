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
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import {
  SubmissionStatus,
  Submission,
  useReturnSubmission,
  useUpdateSubmissionDraft,
} from "@/hooks/use-submissions";

import { useTranslation } from "react-i18next";

export function formatShortDate(date: Date, lang: string) {
  const sameYear = date.getFullYear() === new Date().getFullYear();

  return new Intl.DateTimeFormat(lang, {
    day: "2-digit",
    month: "short",
    ...(sameYear ? {} : { year: "numeric" }),
  }).format(date);
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
  returned: <CircleCheck size={defaultSize} />,
  excused: <CircleCheck size={defaultSize} />,
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
  returned: "blue-500",
  excused: "gray-500",
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
  const icon = STATUS_ICONS[statusKey] ?? <Circle size={defaultSize} />;

  const labelKey = `status.${status === "needs_review" ? "needsReview" : status}`;
  const label = t([labelKey, 'status.unknown']);

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
      className={`bg-gray-200 dark:bg-accent h-2 w-8 rounded-md ${animate ? "animate-pulse" : ""}`}
    ></div>
  );
};

export function InlineEditableScore({ submission }: { submission: Submission }) {
  const { t } = useTranslation();
  const updateDraft = useUpdateSubmissionDraft();
  const inputRef = useRef<HTMLInputElement>(null);
  const scoreValue = submission.draftScore ?? null;
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(
    scoreValue !== null && scoreValue !== undefined ? String(scoreValue) : "",
  );

  useEffect(() => {
    if (!isEditing) {
      setValue(
        scoreValue !== null && scoreValue !== undefined ? String(scoreValue) : "",
      );
    }
  }, [isEditing, scoreValue]);

  useEffect(() => {
    if (isEditing) {
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [isEditing]);

  const isDisabled = submission.status === "pending" || updateDraft.isPending;
  const commit = () => {
    if (isDisabled) return;
    const trimmed = value.trim();
    const nextScore = trimmed === "" ? null : Number(trimmed);
    if (trimmed !== "" && Number.isNaN(nextScore)) {
      setValue(
        scoreValue !== null && scoreValue !== undefined ? String(scoreValue) : "",
      );
      return;
    }
    const unchanged =
      (nextScore == null && scoreValue == null) ||
      (typeof nextScore === "number" && nextScore === scoreValue);
    if (unchanged) return;
    updateDraft.mutate({
      id: submission.id,
      data: { score: nextScore },
    });
  };

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      <Input
        ref={inputRef}
        type="number"
        inputMode="decimal"
        className={`h-7 w-5 focus:w-10 px-0 py-0 text-end focus:text-start text-sm bg-transparent border-transparent shadow-none focus-visible:border-border focus-visible:ring-1 focus-visible:ring-ring/40 focus-visible:bg-muted/20 focus-visible:px-2 focus-visible:py-1 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:m-0 [&::-webkit-inner-spin-button]:m-0 ${
          scoreValue == null ? "text-muted-foreground italic" : "text-foreground"
        } ${isDisabled ? "cursor-not-allowed opacity-50" : "cursor-text"}`}
        value={value}
        onFocus={() => !isDisabled && setIsEditing(true)}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => {
          setIsEditing(false);
          commit();
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.currentTarget.blur();
          }
          if (event.key === "Escape") {
            setIsEditing(false);
            setValue(
              scoreValue !== null && scoreValue !== undefined
                ? String(scoreValue)
                : "",
            );
          }
        }}
        placeholder="—"
        aria-label={t("submissions.grade")}
        disabled={isDisabled}
      />
      <span className="text-xs text-muted-foreground">/100</span>
    </div>
  );
}

export function InlineEditableFeedback({
  submission,
  startInEditMode,
}: {
  submission: Submission;
  startInEditMode?: boolean;
}) {
  const { t } = useTranslation();
  const updateDraft = useUpdateSubmissionDraft();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const feedbackValue = submission.draftFeedback ?? "";
  const [isEditing, setIsEditing] = useState(startInEditMode || false);
  const [value, setValue] = useState(feedbackValue ?? "");

  useEffect(() => {
    if (!isEditing) {
      setValue(feedbackValue ?? "");
    }
  }, [isEditing, feedbackValue]);

  useEffect(() => {
    if (isEditing) {
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [isEditing]);

  const isDisabled = submission.status === "pending" || updateDraft.isPending;
  const commit = () => {
    if (isDisabled) return;
    if (value === feedbackValue) return;
    updateDraft.mutate({
      id: submission.id,
      data: { feedback: value },
    });
  };

  return (
    <Textarea
      ref={inputRef}
      rows={isEditing ? 6 : 1}
      className={`w-full px-2 py-0 text-sm bg-transparent focus-visible:ring-1 focus-visible:ring-ring/40 focus-visible:bg-muted/20 focus-visible:px-2 focus-visible:py-1 transition-all ${
        isEditing ? "min-h-32 resize-y" : "h-16 min-h-16 resize-none overflow-hidden"
      } ${value ? "text-foreground" : "text-muted-foreground italic"} ${
        isDisabled ? "cursor-not-allowed opacity-50" : "cursor-text"
      }`}
      value={value}
      onFocus={() => !isDisabled && setIsEditing(true)}
      onChange={(event) => setValue(event.target.value)}
      onBlur={() => {
        setIsEditing(false);
        commit();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          setIsEditing(false);
          setValue(feedbackValue ?? "");
          inputRef.current?.blur();
        }
      }}
      placeholder="—"
      aria-label={t("submissions.feedback")}
      disabled={isDisabled}
    />
  );
}

export function useSubmissionColumns(): ColumnDef<Submission>[] {
  const { t, i18n } = useTranslation();

  return useMemo(
    () => [
      {
        id: "select",
        header: ({ table }) => {
          const all = table.getIsAllRowsSelected();
          const some = table.getIsSomeRowsSelected();
          const checkedValue: boolean | "indeterminate" = all
            ? true
            : some
              ? "indeterminate"
              : false;

          return (
            <Checkbox
              checked={checkedValue as any}
              onCheckedChange={(value) => table.toggleAllRowsSelected(!!value)}
              aria-label="Select all"
            />
          );
        },
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        ),
        enableSorting: false,
        enableHiding: false,
      },
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
        accessorKey: "draftScore",
        header: t("submissions.grade"),
        cell: (info) => {
          return <InlineEditableScore submission={info.row.original} />;
        },
      },
      {
        accessorKey: "submittedAt",
        header: t("submissions.submissionDate"),
        cell: (info) => {
          const date = info.getValue() as Date;
          return date ? (
            formatShortDate(new Date(date), i18n.language)
          ) : (
            <SkeletonStatus status={info.cell.row.original.status} />
          );
        },
      },
      {
        accessorKey: "draftFeedback",
        header: t("submissions.feedback"),
        cell: (info) => {
          const feedback = info.getValue() as string;
          return (
            <p
              className="block max-w-[240px] truncate cursor-pointer hover:underline hover:decoration-dotted hover:decoration-gray-500 hover:underline-offset-3"
              onClick={(e) => {
                e.stopPropagation();
                (info.table.options.meta as any)?.onFeedbackClick?.(
                  info.row.original,
                );
              }}
            >
              {feedback || "—"}
            </p>
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
    [t, i18n.language],
  );
}

function SubmissionActionsCell({ submission }: { submission: Submission }) {
  const { t } = useTranslation();
  const { workflows } = useWorkflows();
  const activeWorkflowId = useWorkflowStore((state) => state.activeWorkflowId);
  const returnSubmission = useReturnSubmission();

  const workflow = useMemo(() => {
    if (activeWorkflowId)
      return workflows.find((w) => w.id === activeWorkflowId);
    return workflows[0];
  }, [activeWorkflowId, workflows]);

  const hasDraft =
    submission.draftScore != null || submission.draftFeedback != null;
  const canReturn =
    hasDraft && submission.status !== "returned" && !returnSubmission.isPending;

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
        <DropdownMenuItem
          onClick={() => returnSubmission.mutate(submission.id)}
          disabled={!canReturn}
        >
          <CircleCheck size={16} /> {t("submissions.returnAction")}
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

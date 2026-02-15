import React from "react";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock3,
  FileDiff,
  FileText,
  Pencil,
  Upload,
  User,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { SubmissionEvent, SubmissionEventType } from "@/hooks/use-submissions";
import UserAvatar from "@/components/user-avatar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface TimelineProps {
  timeline?: SubmissionEvent[];
}

const SubmissionTimeline: React.FC<TimelineProps> = ({ timeline }) => {
  const { t, i18n } = useTranslation();

  if (!timeline?.length) {
    return <div>{t("submissions.timelineEvents.labels.noEvents")}</div>;
  }

  const sortedEvents = [...timeline].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
  );

  return (
    <div className="relative ml-4 space-y-8 border-l-2 border-border pb-10">
      {sortedEvents.map((event) => (
        <TimelineItem key={event.id} event={event} t={t} locale={i18n.language} />
      ))}
    </div>
  );
};

const TimelineItem = ({
  event,
  t,
  locale,
}: {
  event: SubmissionEvent;
  t: (key: string, options?: Record<string, unknown>) => string;
  locale: string;
}) => {
  const renderer = EVENT_RENDERERS[event.eventType] ?? DEFAULT_RENDERER;
  const { icon: Icon, color } = renderer;

  let actorName = t("submissions.timelineEvents.actor.system");
  if (event.actor?.name) {
    actorName = event.actor.name;
  } else if (event.workflowRun) {
    actorName =
      event.workflowRun.runner?.name ||
      t("submissions.timelineEvents.actor.automation");
  }

  const body = renderer.renderBody?.({ event, t });
  const time = formatEventTime(event.createdAt, locale);

  return (
    <div className="relative pl-8">
      <div
        className={cn(
          "absolute -left-[21px] top-0 flex h-10 w-10 items-center justify-center rounded-full border bg-background ring-4 ring-background",
          color,
        )}
      >
        <Icon size={18} />
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <UserAvatar size="sm" username={actorName} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-0.5 font-semibold text-foreground">{actorName}</span>
              {renderer.renderInline({ event, t })}
              <span className="inline-flex items-center gap-1 text-xs opacity-70">
                <Clock3 className="h-3 w-3" />
                {time}
              </span>
            </div>
            {body && <div className="mt-2">{body}</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

type EventRenderContext = {
  event: SubmissionEvent;
  t: (key: string, options?: Record<string, unknown>) => string;
};

type EventRenderer = {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  renderInline: (ctx: EventRenderContext) => React.ReactNode;
  renderBody?: (ctx: EventRenderContext) => React.ReactNode;
};

const EVENT_RENDERERS: Partial<Record<SubmissionEventType, EventRenderer>> = {
  submission_submitted: {
    icon: Upload,
    color:
      "border-blue-200 bg-blue-100 text-blue-600 dark:border-blue-700 dark:bg-blue-900 dark:text-blue-300",
    renderInline: ({ event, t }) => {
      const artifactCount = getNumberField(event.details, "artifact_count");
      return (
        <span>
          {t("submissions.timelineEvents.actions.submitted")}
          {typeof artifactCount === "number" && (
            <span className="ml-1">
              {t("submissions.timelineEvents.actions.withArtifacts", {
                count: artifactCount,
              })}
            </span>
          )}
        </span>
      );
    },
  },
  status_transitioned: {
    icon: ArrowRight,
    color:
      "border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300",
    renderInline: ({ event, t }) => {
      const fromStatus = getStringField(event.details, "from_status");
      const toStatus = getStringField(event.details, "to_status");
      return (
        <span>
          {t("submissions.timelineEvents.actions.statusTransitioned", {
            from: formatStatusLabel(fromStatus, t),
            to: formatStatusLabel(toStatus, t),
          })}
        </span>
      );
    },
  },
  ai_initial_result_recorded: {
    icon: Bot,
    color:
      "border-indigo-200 bg-indigo-100 text-indigo-600 dark:border-indigo-700 dark:bg-indigo-900 dark:text-indigo-300",
    renderInline: ({ event, t }) => {
      const attemptIndex = getNumberField(event.details, "attempt_index");
      return (
        <span>
          {t("submissions.timelineEvents.actions.aiInitialResult")}
          {typeof attemptIndex === "number" && (
            <span className="ml-1">
              {t("submissions.timelineEvents.actions.attempt", {
                value: attemptIndex,
              })}
            </span>
          )}
        </span>
      );
    },
  },
  ai_regrade_result_recorded: {
    icon: Bot,
    color:
      "border-indigo-200 bg-indigo-100 text-indigo-600 dark:border-indigo-700 dark:bg-indigo-900 dark:text-indigo-300",
    renderInline: ({ event, t }) => {
      const attemptIndex = getNumberField(event.details, "attempt_index");
      return (
        <span>
          {t("submissions.timelineEvents.actions.aiRegradeResult")}
          {typeof attemptIndex === "number" && (
            <span className="ml-1">
              {t("submissions.timelineEvents.actions.attempt", {
                value: attemptIndex,
              })}
            </span>
          )}
        </span>
      );
    },
  },
  draft_manually_edited: {
    icon: Pencil,
    color:
      "border-amber-200 bg-amber-100 text-amber-600 dark:border-amber-700 dark:bg-amber-900 dark:text-amber-300",
    renderInline: ({ event, t }) => {
      const score = getScoreChange(event.details);
      const feedback = getFeedbackChange(event.details);
      const hasScore = !!score;
      const hasFeedback = !!feedback;

      if (hasScore && hasFeedback) {
        return <span>{t("submissions.timelineEvents.actions.editedScoreAndFeedback")}</span>;
      }

      if (hasScore && score) {
        const diff = (score.new ?? 0) - (score.old ?? 0);
        return (
          <span className="inline-flex items-center gap-1.5">
            {t("submissions.timelineEvents.actions.scoreChanged", {
              from: formatScore(score.old),
              to: formatScore(score.new),
            })}
            {diff !== 0 && (
              <Badge
                variant={diff > 0 ? "default" : "destructive"}
                className="h-5 px-1.5 text-[10px]"
              >
                {diff > 0 ? "+" : ""}
                {diff}
              </Badge>
            )}
          </span>
        );
      }

      if (hasFeedback) {
        return <span>{t("submissions.timelineEvents.actions.feedbackEdited")}</span>;
      }

      return <span>{t("submissions.timelineEvents.actions.draftEdited")}</span>;
    },
    renderBody: ({ event, t }) => {
      const feedback = getFeedbackChange(event.details);
      if (!feedback) {
        return null;
      }
      return <FeedbackDiffWidget feedback={feedback} t={t} />;
    },
  },
  returned_to_student: {
    icon: CheckCircle2,
    color:
      "border-green-200 bg-green-100 text-green-600 dark:border-green-700 dark:bg-green-900 dark:text-green-300",
    renderInline: ({ event, t }) => {
      const publishedScore = getNumberField(event.details, "published_score");
      return (
        <span>
          {t("submissions.timelineEvents.actions.returnedToStudent")}
          {typeof publishedScore === "number" && (
            <span className="ml-1">
              {t("submissions.timelineEvents.actions.withScore", {
                score: publishedScore,
              })}
            </span>
          )}
        </span>
      );
    },
    renderBody: ({ event, t }) => {
      const feedback = getStringField(event.details, "published_feedback");
      if (!feedback) {
        return null;
      }
      return <ReturnedFeedbackDetails feedback={feedback} t={t} />;
    },
  },
};

const DEFAULT_RENDERER: EventRenderer = {
  icon: User,
  color:
    "border-gray-200 bg-gray-100 text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400",
  renderInline: ({ t }) => (
    <span>{t("submissions.timelineEvents.actions.unknownEvent")}</span>
  ),
  renderBody: ({ event, t }) => {
    if (!event.details) return null;
    return <RawDetails details={event.details} t={t} />;
  },
};

const FeedbackDiffWidget = ({
  feedback,
  t,
}: {
  feedback: { old: string | null; new: string | null };
  t: (key: string, options?: Record<string, unknown>) => string;
}) => {
  const [showOld, setShowOld] = React.useState(false);

  return (
    <div className="group overflow-hidden rounded-md border border-border bg-card">
      <div className="flex items-center justify-between border-b bg-muted/30 px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Pencil className="h-3 w-3" />
          {t("submissions.timelineEvents.labels.feedbackEdited")}
        </div>
        <button
          onClick={() => setShowOld((prev) => !prev)}
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <FileDiff className="h-3 w-3" />
          {showOld
            ? t("submissions.timelineEvents.labels.hidePrevious")
            : t("submissions.timelineEvents.labels.compare")}
        </button>
      </div>

      <div className="space-y-3 p-3 text-sm">
        {showOld && (
          <div className="rounded border border-border p-2 text-xs text-red-800 line-through">
            {feedback.old || t("submissions.timelineEvents.labels.empty")}
          </div>
        )}
        <div
          className={cn(
            "text-foreground",
            showOld && "rounded border border-border p-2 text-green-900",
          )}
        >
          {feedback.new || t("submissions.timelineEvents.labels.empty")}
        </div>
      </div>
    </div>
  );
};

const ReturnedFeedbackDetails = ({
  feedback,
  t,
}: {
  feedback: string;
  t: (key: string, options?: Record<string, unknown>) => string;
}) => {
  const [open, setOpen] = React.useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline">
        <FileText className="h-3.5 w-3.5" />
        {open
          ? t("submissions.timelineEvents.labels.hideFeedback")
          : t("submissions.timelineEvents.labels.showFeedback")}
        {open ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 rounded-md border border-border bg-card px-3 py-2 text-sm">
        {feedback}
      </CollapsibleContent>
    </Collapsible>
  );
};

const RawDetails = ({
  details,
  t,
}: {
  details: Record<string, unknown>;
  t: (key: string, options?: Record<string, unknown>) => string;
}) => {
  const [open, setOpen] = React.useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline">
        {open
          ? t("submissions.timelineEvents.labels.hideDetails")
          : t("submissions.timelineEvents.labels.showDetails")}
        {open ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="mt-2 overflow-x-auto rounded bg-muted p-2 text-xs">
          {JSON.stringify(details, null, 2)}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  );
};

function formatEventTime(createdAt: string, locale: string) {
  return new Date(createdAt).toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatStatusLabel(
  status: string | null,
  t: (key: string, options?: Record<string, unknown>) => string,
) {
  if (!status) {
    return t("submissions.timelineEvents.labels.unknown");
  }

  const statusKey = status === "needs_review" ? "needsReview" : status;
  return t(`status.${statusKey}`);
}

function formatScore(value: number | null) {
  if (value == null) return "-";
  return String(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getScoreChange(
  details: SubmissionEvent["details"],
): { old: number | null; new: number | null } | null {
  if (!isRecord(details)) return null;
  const score = details.score;
  if (!isRecord(score)) return null;
  const oldValue = typeof score.old === "number" ? score.old : null;
  const newValue = typeof score.new === "number" ? score.new : null;
  return { old: oldValue, new: newValue };
}

function getFeedbackChange(
  details: SubmissionEvent["details"],
): { old: string | null; new: string | null } | null {
  if (!isRecord(details)) return null;
  const feedback = details.feedback;
  if (!isRecord(feedback)) return null;
  const oldValue = typeof feedback.old === "string" ? feedback.old : null;
  const newValue = typeof feedback.new === "string" ? feedback.new : null;
  return { old: oldValue, new: newValue };
}

function getStringField(details: SubmissionEvent["details"], key: string) {
  if (!isRecord(details)) return null;
  const value = details[key];
  return typeof value === "string" ? value : null;
}

function getNumberField(details: SubmissionEvent["details"], key: string) {
  if (!isRecord(details)) return null;
  const value = details[key];
  return typeof value === "number" ? value : null;
}

export default SubmissionTimeline;

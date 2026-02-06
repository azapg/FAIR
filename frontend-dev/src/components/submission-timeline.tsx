import React from "react";
import {
  CheckCircle2,
  User,
  RotateCcw,
  ArrowRight,
  Pencil,
  FileDiff,
  TrendingUp,
  TrendingDown,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SubmissionEvent, SubmissionEventType } from "@/hooks/use-submissions";
import UserAvatar from "./user-avatar";

interface TimelineProps {
  timeline?: SubmissionEvent[];
}

const SubmissionTimeline: React.FC<TimelineProps> = ({ timeline }) => {
  if (!timeline?.length) return <div>No events.</div>;

  const sortedEvents = [...timeline].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
  );

  return (
    <div className="relative border-l-2 border-border ml-4 space-y-8 pb-10">
      {sortedEvents.map((event, index) => (
        <TimelineItem
          key={event.id}
          event={event}
          isLast={index === sortedEvents.length - 1}
        />
      ))}
    </div>
  );
};

const TimelineItem = ({
  event,
  isLast,
}: {
  event: SubmissionEvent;
  isLast: boolean;
}) => {
  const { icon: Icon, color, title } = getEventMeta(event);

  let actorName;
  if (event.actorId && !event.workflowRunId) {
    actorName = "Instructor";
  } else if (event.workflowRunId) {
    // TODO: Right now we only have access to the workflow run id, but backend should hydrate
    // that with WorkflowRunRead so we can have access to the person who ran it.
    actorName = event.workflowRunId;
  } else {
    actorName = "System";
  }

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

      <div className="flex flex-col gap-2">
        <div className="flex align-center gap-2 text-muted-foreground">
          <UserAvatar size="sm" username="Allan Zapata" />
          <div>
            <span className="font-semibold text-foreground mr-1">
              {actorName}
            </span>
            {title}
            <span className="ml-2 text-xs opacity-70">
              {new Date(event.createdAt).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>

        <div className="w-full max-w-2xl">{renderEventBody(event)}</div>
      </div>
    </div>
  );
};

function renderEventBody(event: SubmissionEvent) {
  switch (event.eventType) {
    case "returned":
      return <ReturnedCard details={event.details} />;

    case "manual_edit":
      // manual_edit is tricky: it can be a score change OR a feedback change.
      // We detect this by inspecting the 'details' keys.
      if (event.details?.score) {
        return <ScoreChangeWidget score={event.details.score} />;
      }
      if (event.details?.feedback) {
        return <FeedbackDiffWidget feedback={event.details.feedback} />;
      }
      return (
        <div className="text-sm italic text-muted-foreground">
          Edited submission details
        </div>
      );

    case "ai_graded":
      return null;

    case "initial_result":
      return null;

    default:
      // Fallback for debugging
      return event.details ? (
        <pre className="text-xs bg-muted p-2 rounded">
          {JSON.stringify(event.details)}
        </pre>
      ) : null;
  }
}

const ReturnedCard = ({ details }: { details: any }) => (
  <Card className="border-blue-200 dark:border-blue-500 shadow-sm gap-0">
    <CardHeader>
      <div className="flex justify-between items-center">
        <CardTitle className="font-medium text-lg flex items-center gap-2">
          Submission Returned
        </CardTitle>
        <Badge
          variant="outline"
          className="bg-white dark:bg-gray-800 border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300 font-bold"
        >
          {details.published_score}/100
        </Badge>
      </div>
    </CardHeader>
    <CardContent>
      <p>{details.published_feedback}</p>
    </CardContent>
  </Card>
);

const ScoreChangeWidget = ({
  score,
}: {
  score: { old: number; new: number };
}) => {
  const diff = score.new - score.old;
  const isPositive = diff > 0;

  return (
    <div className="flex items-center gap-3 text-sm border rounded-md px-3 py-2 w-fit bg-card">
      <span className="text-muted-foreground flex items-center gap-1">
        Score Update:
      </span>
      <span className="line-through text-muted-foreground">{score.old}</span>
      <ArrowRight className="h-3 w-3 text-muted-foreground" />
      <span className="font-bold font-mono">{score.new}</span>

      <Badge
        variant={isPositive ? "default" : "destructive"}
        className="h-5 px-1.5 text-[10px] ml-2"
      >
        {isPositive ? "+" : ""}
        {diff}
      </Badge>
    </div>
  );
};

const FeedbackDiffWidget = ({
  feedback,
}: {
  feedback: { old: string; new: string };
}) => {
  const [showOld, setShowOld] = React.useState(false);

  return (
    <div className="group rounded-md border border-border bg-card overflow-hidden">
      <div className="bg-muted/30 px-3 py-2 border-b flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Pencil className="h-3 w-3" />
          Feedback Edited
        </div>
        <button
          onClick={() => setShowOld(!showOld)}
          className="text-sm text-blue-500 hover:underline flex items-center gap-1"
        >
          <FileDiff className="h-3 w-3" />
          {showOld ? "Hide Previous" : "Compare"}
        </button>
      </div>

      <div className="p-3 text-sm space-y-3">
        {showOld && (
          <div className="p-2 rounded border border-border text-red-800 text-xs line-through">
            {feedback.old}
          </div>
        )}
        <div
          className={cn(
            "text-foreground",
            showOld &&
              "p-2 rounded border border-border text-green-900",
          )}
        >
          {feedback.new}
        </div>
      </div>
    </div>
  );
};

function getEventMeta(event: SubmissionEvent) {
  switch (event.eventType) {
    case "returned":
      return {
        icon: CheckCircle2,
        color: "text-green-600 dark:text-green-400 border-green-200 dark:border-green-700 bg-green-100 dark:bg-green-900",
        title: "returned the submission",
      };
    case "manual_edit":
      return {
        icon: Pencil,
        color: "text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-700 bg-amber-100 dark:bg-amber-900",
        title: "made a change",
      };
    case "ai_graded":
      return {
        icon: FileDiff,
        color: "text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-700 bg-purple-100 dark:bg-purple-900",
        title: "AI processed results",
      };
    default:
      return {
        icon: User,
        color: "text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800",
        title: "updated submission",
      };
  }
}

export default SubmissionTimeline;

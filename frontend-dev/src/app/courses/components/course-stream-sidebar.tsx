import type { ReactNode } from "react";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Assignment } from "@/hooks/use-assignments";
import { useGradingQueue } from "@/hooks/use-lms";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function ReviewSummary({ courseId }: { courseId: string }) {
  const { data, isPending, isError, refetch } = useGradingQueue(courseId);
  return (
    <section
      className="flex flex-col items-start gap-2 rounded-xl bg-muted/70 p-4"
      aria-label="Submissions to review"
    >
      {isPending ? (
        <Skeleton className="h-8 w-12" />
      ) : isError ? (
        <p className="text-sm text-muted-foreground">
          Review count unavailable
        </p>
      ) : (
        <span className="text-3xl tracking-tight">{data?.length ?? 0}</span>
      )}
      {!isError && (
        <p className="text-xs text-muted-foreground">submissions to review</p>
      )}
      {isError ? (
        <Button
          variant="link"
          size="sm"
          className="px-0"
          onClick={() => {
            void refetch();
          }}
        >
          Try again
        </Button>
      ) : (
        <Link
          className="inline-flex items-center gap-1 text-xs hover:underline"
          to={`/courses/${courseId}/gradebook`}
        >
          Open gradebook <ArrowRight className="size-3" />
        </Link>
      )}
    </section>
  );
}

export function CourseStreamSidebar({
  courseId,
  assignments,
  canReview,
  enrollmentControls,
}: {
  courseId: string;
  assignments: Assignment[];
  canReview: boolean;
  enrollmentControls?: ReactNode;
}) {
  const upcoming = assignments
    .filter(
      (a) =>
        a.status === "published" &&
        a.deadline &&
        new Date(a.deadline).getTime() >= Date.now(),
    )
    .sort(
      (a, b) =>
        new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime(),
    )
    .slice(0, 3);
  return (
    <aside
      className="grid grid-cols-2 items-start gap-3 md:flex md:flex-col md:gap-4 [&>section]:w-full"
      aria-label="Course essentials"
    >
      {canReview && <ReviewSummary courseId={courseId} />}
      {enrollmentControls}
      <section
        className={`col-span-full flex-col gap-5 pt-2 ${canReview ? "hidden md:flex" : "flex"}`}
      >
        <h2 className="text-sm font-medium">Coming up</h2>
        {upcoming.map((assignment) => (
          <Link
            key={assignment.id}
            className="flex flex-col gap-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            to={`/courses/${courseId}/assignments/${assignment.id}`}
          >
            <span className="text-xs text-muted-foreground">
              {new Date(assignment.deadline!).toLocaleDateString(undefined, {
                weekday: "short",
                month: "short",
                day: "numeric",
              })}{" "}
              ·{" "}
              {new Date(assignment.deadline!).toLocaleTimeString(undefined, {
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
            <span className="text-sm font-medium hover:underline">
              {assignment.title}
            </span>
          </Link>
        ))}
        {!upcoming.length && (
          <p className="text-xs text-muted-foreground">
            No upcoming deadlines.
          </p>
        )}
        <Link
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          to={`/courses/${courseId}/assignments`}
        >
          All assignments <ArrowRight className="size-3" />
        </Link>
      </section>
    </aside>
  );
}

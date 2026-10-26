import { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  ListFilter,
  MessageSquare,
  Plus,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Badge } from "@/components/ui/badge";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ArtifactAction } from "@/components/artifact-action";
import type { Assignment } from "@/hooks/use-assignments";
import { useCourseContent } from "@/hooks/use-course-content";
import {
  CoursePost,
  useCoursePosts,
  useCreateCoursePost,
  useCreatePostComment,
  usePostComments,
} from "@/hooks/use-communication";

function PostComments({ post }: { post: CoursePost }) {
  const [body, setBody] = useState("");
  const {
    data: comments = [],
    isPending,
    isError,
    refetch,
  } = usePostComments(post.id);
  const createComment = useCreatePostComment(post.id);
  return (
    <div className="mt-4 flex flex-col gap-3">
      {isPending && (
        <p className="text-xs text-muted-foreground">Loading comments…</p>
      )}
      {isError && (
        <Button
          variant="link"
          size="sm"
          onClick={() => {
            void refetch();
          }}
        >
          Retry loading comments
        </Button>
      )}
      {comments.map((comment) => (
        <p key={comment.id} className="text-sm">
          <span className="font-medium">{comment.authorName}</span>{" "}
          <span className="whitespace-pre-wrap text-muted-foreground">
            {comment.body}
          </span>
        </p>
      ))}
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (body.trim())
            createComment.mutate(body.trim(), { onSuccess: () => setBody("") });
        }}
      >
        <Input
          aria-label="Class comment"
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Add a class comment…"
        />
        <Button
          variant="outline"
          type="submit"
          disabled={!body.trim() || createComment.isPending}
        >
          Comment
        </Button>
      </form>
      {createComment.isError && (
        <p role="alert" className="text-sm text-destructive">
          Could not post your comment. Please try again.
        </p>
      )}
    </div>
  );
}

function PostCard({ post }: { post: CoursePost }) {
  const [commentsOpen, setCommentsOpen] = useState(false);
  return (
    <article className="rounded-xl border border-border/70 bg-card p-5">
      <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        <span>{post.authorName}</span>
        <span>· {post.kind === "material" ? "Material" : "Announcement"}</span>
        <time className="ml-auto" dateTime={post.createdAt}>
          {new Date(post.createdAt).toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </time>
      </div>
      <h3 className="text-base font-medium">{post.title}</h3>
      {post.body && (
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
          {post.body}
        </p>
      )}
      {!!post.artifacts?.length && (
        <div className="mt-3 flex flex-wrap gap-2">
          {post.artifacts.map((artifact) => (
            <ArtifactAction
              key={artifact.id}
              artifact={artifact}
              label={artifact.title ?? "Attachment"}
              variant="outline"
            />
          ))}
        </div>
      )}
      <div className="mt-4 flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          aria-expanded={commentsOpen}
          onClick={() => setCommentsOpen(!commentsOpen)}
        >
          <MessageSquare />{" "}
          {post.commentsCount ? `${post.commentsCount} comments` : "Comment"}
        </Button>
      </div>
      {commentsOpen && <PostComments post={post} />}
    </article>
  );
}

type StreamFilter = "all" | "announcements" | "assignments" | "materials";
const FILTERS: Record<StreamFilter, string> = {
  all: "All activity",
  announcements: "Announcements",
  assignments: "Assignments",
  materials: "Materials",
};

export function StreamTab({
  courseId,
  canPost,
  assignments = [],
  assignmentsLoading = false,
  assignmentsError = false,
  onRetryAssignments,
  onCreateAssignment,
  composerOpen,
  onComposerOpenChange,
}: {
  courseId: string;
  canPost: boolean;
  assignments?: Assignment[];
  assignmentsLoading?: boolean;
  assignmentsError?: boolean;
  onRetryAssignments?: () => void;
  onCreateAssignment?: () => void;
  composerOpen?: boolean;
  onComposerOpenChange?: (open: boolean) => void;
}) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [localComposerOpen, setLocalComposerOpen] = useState(false);
  const [filter, setFilter] = useState<StreamFilter>("all");
  const postsQuery = useCoursePosts(courseId);
  const contentQuery = useCourseContent(courseId);
  const createPost = useCreateCoursePost(courseId);
  const showComposer = canPost && (composerOpen ?? localComposerOpen);
  const setComposer = (open: boolean) => {
    setLocalComposerOpen(open);
    onComposerOpenChange?.(open);
  };
  const posts = (postsQuery.data ?? []).map((post) => ({
    id: `post-${post.id}`,
    kind: post.kind === "material" ? "materials" : "announcements",
    date: post.createdAt,
    content: <PostCard post={post} />,
  }));
  const assignmentEvents = assignments
    .filter((a) => a.status === "published")
    .map((assignment) => ({
      id: `assignment-${assignment.id}`,
      kind: "assignments",
      date: assignment.publishedAt ?? assignment.createdAt,
      content: (
        <article className="rounded-xl border border-border/70 bg-card p-5">
          <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
            <ClipboardList className="size-3.5" />
            New assignment
            <time
              className="ml-auto"
              dateTime={assignment.publishedAt ?? assignment.createdAt}
            >
              {new Date(
                assignment.publishedAt ?? assignment.createdAt,
              ).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </time>
          </div>
          <h3 className="text-base font-medium">
            <Link
              className="hover:underline"
              to={`/courses/${courseId}/assignments/${assignment.id}`}
            >
              {assignment.title}
            </Link>
          </h3>
          {assignment.description && (
            <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
              {assignment.description}
            </p>
          )}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            {assignment.deadline && (
              <Badge variant="secondary">
                Due{" "}
                {new Date(assignment.deadline).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })}
              </Badge>
            )}
            <Link
              className="ml-auto inline-flex items-center gap-1 text-xs hover:underline"
              to={`/courses/${courseId}/assignments/${assignment.id}`}
            >
              Open assignment <ArrowRight className="size-3" />
            </Link>
          </div>
        </article>
      ),
    }));
  const materials = (contentQuery.data?.sections ?? [])
    .filter((section) => section.visibility === "published")
    .flatMap((section) => section.items)
    .filter(
      (item) =>
        item.visibility === "published" &&
        item.kind !== "heading" &&
        item.kind !== "assignment",
    )
    .map((item) => ({
      id: `material-${item.id}`,
      kind: "materials",
      date: item.createdAt,
      content: (
        <article className="rounded-xl border border-border/70 bg-card p-5">
          <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
            <BookOpen className="size-3.5" />
            New material
            <time className="ml-auto" dateTime={item.createdAt}>
              {new Date(item.createdAt).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </time>
          </div>
          <h3 className="text-base font-medium">
            <Link
              className="hover:underline"
              to={`/courses/${courseId}/content`}
            >
              {item.title}
            </Link>
          </h3>
          <Link
            className="mt-4 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            to={`/courses/${courseId}/content`}
          >
            View material <ArrowRight className="size-3" />
          </Link>
        </article>
      ),
    }));
  const events = [...posts, ...assignmentEvents, ...materials]
    .filter((event) => filter === "all" || event.kind === filter)
    .sort(
      (a, b) =>
        new Date(b.date).getTime() - new Date(a.date).getTime() ||
        a.id.localeCompare(b.id),
    );
  const loading =
    ((filter === "all" ||
      filter === "announcements" ||
      filter === "materials") &&
      postsQuery.isPending) ||
    ((filter === "all" || filter === "materials") && contentQuery.isPending) ||
    ((filter === "all" || filter === "assignments") && assignmentsLoading);
  const errors = [
    {
      show:
        (filter === "all" ||
          filter === "announcements" ||
          filter === "materials") &&
        postsQuery.isError,
      label: "Posts",
      retry: () => {
        void postsQuery.refetch();
      },
    },
    {
      show:
        (filter === "all" || filter === "materials") && contentQuery.isError,
      label: "Materials",
      retry: () => {
        void contentQuery.refetch();
      },
    },
    {
      show: (filter === "all" || filter === "assignments") && assignmentsError,
      label: "Assignments",
      retry: onRetryAssignments,
    },
  ].filter((error) => error.show);

  return (
    <div className="flex min-w-0 flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-medium">Stream</h2>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                aria-label={
                  filter === "all"
                    ? "Filter stream"
                    : `Filter stream: ${FILTERS[filter]}`
                }
                title="Filter stream"
              >
                <ListFilter />
                {filter !== "all" && (
                  <span className="absolute right-1 top-1 size-1.5 rounded-full bg-foreground" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Show</DropdownMenuLabel>
              <DropdownMenuRadioGroup
                value={filter}
                onValueChange={(value) => setFilter(value as StreamFilter)}
              >
                {Object.entries(FILTERS).map(([value, label]) => (
                  <DropdownMenuRadioItem key={value} value={value}>
                    {label}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
          {canPost && onCreateAssignment && (
            <Button onClick={onCreateAssignment}>
              <Plus /> Assignment
            </Button>
          )}
        </div>
      </div>
      {canPost &&
        (showComposer ? (
          <form
            className="flex flex-col gap-4 rounded-xl border bg-card p-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!title.trim()) return;
              createPost.mutate(
                {
                  title: title.trim(),
                  body: body.trim(),
                  kind: "announcement",
                },
                {
                  onSuccess: () => {
                    setTitle("");
                    setBody("");
                    setComposer(false);
                  },
                },
              );
            }}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Share with your class</h3>
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                aria-label="Close composer"
                disabled={createPost.isPending}
                onClick={() => setComposer(false)}
              >
                <X />
              </Button>
            </div>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="course-post-title">Title</FieldLabel>
                <Input
                  id="course-post-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="course-post-body">Message</FieldLabel>
                <Textarea
                  id="course-post-body"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  placeholder="Announcement or instructions"
                />
              </Field>
            </FieldGroup>
            {createPost.isError && (
              <p role="alert" className="text-sm text-destructive">
                Could not post your announcement. Please try again.
              </p>
            )}
            <Button
              className="self-start"
              type="submit"
              disabled={!title.trim() || createPost.isPending}
            >
              {createPost.isPending ? "Posting…" : "Post"}
            </Button>
          </form>
        ) : (
          <button
            className="flex w-full items-center gap-3 rounded-xl border border-border/70 bg-card px-4 py-4 text-left text-sm text-muted-foreground hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => setComposer(true)}
          >
            <MessageSquare className="size-4" />
            Share with your class…
          </button>
        ))}
      {filter !== "all" && (
        <p className="text-xs text-muted-foreground">
          {FILTERS[filter]}
          <Button variant="link" size="xs" onClick={() => setFilter("all")}>
            Show all
          </Button>
        </p>
      )}
      {errors.map((error) => (
        <div
          key={error.label}
          role="alert"
          className="flex items-center justify-between gap-3 text-sm text-muted-foreground"
        >
          <span>{error.label} could not be loaded.</span>
          <Button variant="link" size="sm" onClick={error.retry}>
            Try again
          </Button>
        </div>
      ))}
      {loading && <Skeleton className="h-24 w-full rounded-xl" />}
      {events.map((event) => (
        <div key={event.id}>{event.content}</div>
      ))}
      {!loading && !errors.length && !events.length && (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>
              {filter === "all"
                ? "No activity yet"
                : `No ${FILTERS[filter].toLowerCase()} yet`}
            </EmptyTitle>
            <EmptyDescription>
              {filter === "all"
                ? "Announcements, published assignments, and materials will appear here."
                : "Try showing all activity."}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </div>
  );
}

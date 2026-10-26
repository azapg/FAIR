import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeFileSync } from "node:fs";
import type { Assignment } from "@/hooks/use-assignments";
import { StreamTab } from "./stream-tab";
import { CourseStreamSidebar } from "../components/course-stream-sidebar";
import { EnrollmentControls } from "../components/enrollment-controls";

const mocks = vi.hoisted(() => ({
  postsError: false,
  contentError: false,
  createPost: vi.fn(),
  comments: vi.fn(),
  refetchPosts: vi.fn(),
}));
vi.mock("@/hooks/use-communication", () => ({
  useCoursePosts: () => ({
    data: [
      {
        id: "post-1",
        title: "A quick note before you start",
        body: "Start with something small that you actually want to use. We’ll share what everyone has built on Friday.",
        authorName: "Allan Zapata",
        kind: "announcement",
        commentsCount: 2,
        artifacts: [],
        createdAt: "2026-10-25T08:00:00Z",
      },
    ],
    isPending: false,
    isError: mocks.postsError,
    refetch: mocks.refetchPosts,
  }),
  useCreateCoursePost: () => ({ mutate: mocks.createPost, isPending: false }),
  usePostComments: () => {
    mocks.comments();
    return { data: [], isPending: false };
  },
  useCreatePostComment: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("@/hooks/use-course-content", () => ({
  useCourseContent: () => ({
    data: {
      sections: [
        {
          visibility: "published",
          items: [
            {
              id: "file-1",
              title: "Prompting: a practical guide",
              kind: "file",
              visibility: "published",
              createdAt: "2026-10-24T08:00:00Z",
            },
            {
              id: "hidden",
              title: "Hidden material",
              kind: "page",
              visibility: "hidden",
              createdAt: "2026-10-25T10:00:00Z",
            },
            {
              id: "assignment-link",
              title: "Duplicate assignment link",
              kind: "assignment",
              visibility: "published",
              createdAt: "2026-10-25T09:00:00Z",
            },
          ],
        },
        {
          visibility: "draft",
          items: [
            {
              id: "draft-section-item",
              title: "Material in draft section",
              kind: "file",
              visibility: "published",
              createdAt: "2026-10-26T08:00:00Z",
            },
          ],
        },
      ],
    },
    isPending: false,
    isError: mocks.contentError,
    refetch: vi.fn(),
  }),
}));
vi.mock("@/hooks/use-lms", () => ({
  useGradingQueue: () => ({
    data: Array.from({ length: 6 }, (_, id) => ({ submissionId: String(id) })),
    isPending: false,
    isError: false,
  }),
}));
vi.mock("@/components/artifact-action", () => ({ ArtifactAction: () => null }));

const assignments: Assignment[] = [
  {
    id: "assignment-1",
    courseId: "course-1",
    title: "Build your first AI prototype",
    description:
      "Turn an idea into a working prototype. Share what you built and the prompts that helped you get there.",
    status: "published",
    publishedAt: "2026-10-25T09:00:00Z",
    createdAt: "2026-10-22T08:00:00Z",
    updatedAt: "2026-10-25T09:00:00Z",
    deadline: "2026-10-30T23:59:00Z",
    maxGrade: { type: "points", max: 100 } as unknown as Assignment["maxGrade"],
    allowResubmissions: true,
  },
  {
    id: "draft",
    courseId: "course-1",
    title: "Draft assignment",
    status: "draft",
    createdAt: "2026-10-26T08:00:00Z",
    updatedAt: "2026-10-26T08:00:00Z",
    maxGrade: {} as Assignment["maxGrade"],
    allowResubmissions: false,
  },
];

function mount(canPost = true) {
  return render(
    <MemoryRouter>
      <StreamTab
        courseId="course-1"
        canPost={canPost}
        assignments={assignments}
        onCreateAssignment={vi.fn()}
      />
    </MemoryRouter>,
  );
}
function openFilter() {
  fireEvent.keyDown(screen.getByRole("button", { name: /^Filter stream/ }), {
    key: "ArrowDown",
  });
}

describe("Course stream", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.postsError = false;
    mocks.contentError = false;
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("combines published work and announcements in time order without draft or duplicate content", () => {
    mount();
    const cards = screen.getAllByRole("article");
    expect(
      cards.map((card) => within(card).getByRole("heading").textContent),
    ).toEqual([
      "Build your first AI prototype",
      "A quick note before you start",
      "Prompting: a practical guide",
    ]);
    expect(screen.queryByText("Draft assignment")).not.toBeInTheDocument();
    expect(screen.queryByText("Hidden material")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Material in draft section"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Duplicate assignment link"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open assignment" }),
    ).toHaveAttribute("href", "/courses/course-1/assignments/assignment-1");
    expect(mocks.comments).not.toHaveBeenCalled();
  });

  it("keeps filtering behind the icon and can restore all activity", async () => {
    mount();
    expect(screen.queryByRole("menuitemradio")).not.toBeInTheDocument();
    openFilter();
    fireEvent.click(
      await screen.findByRole("menuitemradio", { name: "Assignments" }),
    );
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "Filter stream: Assignments" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show all" }));
    expect(screen.getAllByRole("article")).toHaveLength(3);
  });

  it("opens the compact composer and submits an announcement", () => {
    mount();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Share with your class…" }),
    );
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Hello class" },
    });
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "See you Friday" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Post" }));
    expect(mocks.createPost).toHaveBeenCalledWith(
      { title: "Hello class", body: "See you Friday", kind: "announcement" },
      expect.any(Object),
    );
  });

  it("keeps posting controls out of the student view", () => {
    mount(false);
    expect(
      screen.queryByRole("button", { name: "Assignment" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Share with your class…" }),
    ).not.toBeInTheDocument();
  });

  it("retains the rest of the feed and offers retry when one source fails", () => {
    mocks.postsError = true;
    mount();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(mocks.refetchPosts).toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Build your first AI prototype" }),
    ).toBeInTheDocument();
  });

  it("can render the implemented Stream and sidebar for visual review", () => {
    if (!process.env.FAIR_COURSE_PROOF) return;
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <div className="mx-auto flex max-w-[1100px] flex-col gap-7 p-6">
          <header className="flex flex-col gap-2">
            <h1 className="text-2xl font-semibold">Intro to Vibecoding</h1>
            <p className="text-sm text-muted-foreground">
              Learn how to vibe code!
            </p>
          </header>
          <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_13rem] md:gap-8">
            <StreamTab
              courseId="course-1"
              canPost
              assignments={assignments}
              onCreateAssignment={() => {}}
            />
            <CourseStreamSidebar
              courseId="course-1"
              assignments={assignments}
              canReview
              enrollmentControls={
                <EnrollmentControls
                  enrollmentCode="F7NB"
                  isEnrollmentEnabled
                  onToggle={async () => {}}
                  onResetCode={async () => {}}
                  isTogglePending={false}
                  isResetPending={false}
                />
              }
            />
          </div>
        </div>
      </MemoryRouter>,
    );
    writeFileSync(process.env.FAIR_COURSE_PROOF, html);
    expect(html).toContain("Class code");
  });
});

const releaseState = vi.hoisted(() => ({ nightly: true }));
vi.mock("@/hooks/use-release-features", () => ({
  useReleaseFeatures: () => ({
    isPending: false,
    channel: releaseState.nightly ? "nightly" : "stable",
    todo: releaseState.nightly,
    inbox: releaseState.nightly,
    extensions: releaseState.nightly,
    course_content: releaseState.nightly,
    gradebook: releaseState.nightly,
    dashboard: releaseState.nightly,
  }),
}));

describe("Stable stream", () => {
  afterEach(() => {
    cleanup();
    releaseState.nightly = true;
  });
  it("keeps announcements and assignments without course-content cards or errors", () => {
    releaseState.nightly = false;
    mocks.contentError = true;
    mount();
    expect(
      screen.queryByText("Prompting: a practical guide"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Build your first AI prototype"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Materials could not/)).not.toBeInTheDocument();
    openFilter();
    expect(
      screen.queryByRole("menuitemradio", { name: "Materials" }),
    ).not.toBeInTheDocument();
  });
});

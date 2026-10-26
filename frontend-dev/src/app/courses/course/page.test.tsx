import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({ ready: false, owner: false }));

vi.mock("@/contexts/auth-context", () => ({
  AuthUserRole: { USER: "user", INSTRUCTOR: "instructor", ADMIN: "admin" },
  useAuth: () => ({
    user: state.owner
      ? { id: "instructor-1", role: "instructor" }
      : { id: "learner-1", role: "user" },
  }),
}));

vi.mock("@/hooks/use-permission", () => ({
  usePermission: () => false,
}));

vi.mock("@/hooks/use-courses", () => ({
  hasStaffCourseMembership: () => false,
  useCourse: () => ({
    isLoading: !state.ready,
    isError: false,
    data: state.ready
      ? {
          id: "course-1",
          name: "Biology",
          description: null,
          instructor: {
            id: "instructor-1",
            name: "Instructor",
            email: "instructor@example.com",
            role: "instructor",
          },
          assignments: [],
          flows: [],
          isArchived: false,
          isEnrollmentEnabled: false,
          membershipRole: "student",
        }
      : undefined,
  }),
  useCourses: () => ({ data: [] }),
  useAssignments: () => ({ data: [] }),
  useResetEnrollmentCode: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateCourseSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("@/hooks/use-assignments", () => ({
  useAssignments: () => ({ data: [] }),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("@/components/page-header", () => ({
  PageHeader: ({
    title,
    children,
    actions,
  }: {
    title: ReactNode;
    children?: ReactNode;
    actions?: ReactNode;
  }) => (
    <header>
      <h1>{title}</h1>
      {actions}
      {children}
    </header>
  ),
}));

vi.mock("@/app/courses/tabs/assignments/assignments-tab", () => ({
  default: () => null,
}));
vi.mock("@/app/courses/tabs/participants-tab", () => ({
  ParticipantsTab: () => null,
}));
vi.mock("@/app/courses/tabs/runs-tab", () => ({ RunsTab: () => null }));
vi.mock("@/app/courses/tabs/artifacts-tab", () => ({
  ArtifactsTab: () => null,
}));
vi.mock("@/app/courses/tabs/flows-tab", () => ({ FlowsTab: () => null }));
vi.mock("@/app/courses/tabs/capabilities-tab", () => ({
  CapabilitiesTab: () => null,
}));
vi.mock("@/app/courses/tabs/gradebook-tab", () => ({
  GradebookTab: () => null,
}));
vi.mock("@/app/courses/tabs/stream-tab", () => ({ StreamTab: () => null }));
vi.mock("@/app/courses/tabs/content/course-content-tab", () => ({
  CourseContentTab: () => null,
}));
vi.mock("@/app/courses/tabs/student-grades-tab", () => ({
  StudentGradesTab: () => null,
}));
vi.mock("@/app/courses/components/course-copy-dialog", () => ({
  CourseCopyDialog: () => null,
}));
vi.mock("@/app/courses/components/enrollment-controls", () => ({
  EnrollmentControls: () => null,
}));
vi.mock("@/app/courses/tabs/assignments/create-assignment-dialog", () => ({
  CreateAssignmentDialog: () => null,
}));

vi.mock("@/app/courses/components/course-stream-sidebar", () => ({
  CourseStreamSidebar: () => null,
}));
vi.mock("@/app/courses/components/course-settings-dialog", () => ({
  CourseSettingsDialog: ({
    initialSection = "general",
    onClose,
  }: {
    initialSection?: string;
    onClose: () => void;
  }) => (
    <div role="dialog">
      <p>{initialSection}</p>
      <button onClick={onClose}>Close settings</button>
    </div>
  ),
}));
import CourseDetailPage from "./page";
function Location() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}
function mount(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/courses/:courseId/:tab?"
          element={
            <>
              <CourseDetailPage />
              <Location />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CourseDetailPage", () => {
  afterEach(cleanup);
  beforeEach(() => {
    state.ready = true;
    state.owner = false;
  });
  it("keeps hooks stable while the course query resolves", () => {
    state.ready = false;
    const view = render(
      <MemoryRouter initialEntries={["/courses/course-1/assignments"]}>
        <Routes>
          <Route
            path="/courses/:courseId/:tab"
            element={<CourseDetailPage />}
          />
        </Routes>
      </MemoryRouter>,
    );

    state.ready = true;
    expect(() =>
      view.rerender(
        <MemoryRouter initialEntries={["/courses/course-1/assignments"]}>
          <Routes>
            <Route
              path="/courses/:courseId/:tab"
              element={<CourseDetailPage />}
            />
          </Routes>
        </MemoryRouter>,
      ),
    ).not.toThrow();

    expect(
      screen.getByRole("heading", { name: "Biology" }),
    ).toBeInTheDocument();
  });
});

describe("Course navigation", () => {
  afterEach(cleanup);
  beforeEach(() => {
    state.ready = true;
    state.owner = true;
  });
  it("opens Stream for a bare course link and the old timeline link", async () => {
    const view = mount("/courses/course-1");
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/courses/course-1/stream",
      ),
    );
    view.unmount();
    mount("/courses/course-1/timeline");
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/courses/course-1/stream",
      ),
    );
  });
  it("limits the teaching navigation to five tabs and moves management into settings", () => {
    mount("/courses/course-1/stream");
    expect(screen.getAllByRole("tab")).toHaveLength(5);
    expect(screen.queryByRole("tab", { name: "Runs" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Copy course" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Course settings" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("general");
  });
  it("preserves technical deep links inside course settings", async () => {
    mount("/courses/course-1/runs");
    expect(screen.getByRole("dialog")).toHaveTextContent("runs");
    fireEvent.click(screen.getByRole("button", { name: "Close settings" }));
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/courses/course-1/stream",
      ),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("keeps course management out of the learner view", async () => {
    state.owner = false;
    mount("/courses/course-1/runs");
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/courses/course-1/stream",
      ),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Course settings" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Grades" })).toBeInTheDocument();
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

describe("Stable course navigation", () => {
  beforeEach(() => {
    releaseState.nightly = false;
    state.ready = true;
    state.owner = true;
  });
  afterEach(() => {
    cleanup();
    releaseState.nightly = true;
  });
  it.each(["content", "gradebook", "runs", "flows", "capabilities"])(
    "redirects hidden %s deep links to Stream",
    async (tab) => {
      mount(`/courses/course-1/${tab}`);
      await waitFor(() =>
        expect(screen.getByTestId("location")).toHaveTextContent(
          "/courses/course-1/stream",
        ),
      );
      expect(screen.getAllByRole("tab")).toHaveLength(3);
      expect(
        screen.queryByRole("tab", { name: "Content" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("tab", { name: "Gradebook" }),
      ).not.toBeInTheDocument();
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    },
  );
  it("hides learner grade summaries and preserves assignments", async () => {
    state.owner = false;
    mount("/courses/course-1/grades");
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/courses/course-1/stream",
      ),
    );
    expect(
      screen.queryByRole("tab", { name: "Grades" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "tabs.assignments" }),
    ).toBeInTheDocument();
  });
});

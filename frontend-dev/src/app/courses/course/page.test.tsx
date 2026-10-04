import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({ ready: false }));

vi.mock("@/contexts/auth-context", () => ({
  AuthUserRole: { USER: "user", INSTRUCTOR: "instructor", ADMIN: "admin" },
  useAuth: () => ({ user: null }),
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
          instructor: { id: "instructor-1", name: "Instructor", email: "instructor@example.com", role: "instructor" },
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
  PageHeader: ({ title, children }: { title: ReactNode; children?: ReactNode }) => (
    <header><h1>{title}</h1>{children}</header>
  ),
}));

vi.mock("@/app/courses/tabs/assignments/assignments-tab", () => ({ default: () => null }));
vi.mock("@/app/courses/tabs/participants-tab", () => ({ ParticipantsTab: () => null }));
vi.mock("@/app/courses/tabs/runs-tab", () => ({ RunsTab: () => null }));
vi.mock("@/app/courses/tabs/artifacts-tab", () => ({ ArtifactsTab: () => null }));
vi.mock("@/app/courses/tabs/flows-tab", () => ({ FlowsTab: () => null }));
vi.mock("@/app/courses/tabs/capabilities-tab", () => ({ CapabilitiesTab: () => null }));
vi.mock("@/app/courses/tabs/gradebook-tab", () => ({ GradebookTab: () => null }));
vi.mock("@/app/courses/tabs/stream-tab", () => ({ StreamTab: () => null }));
vi.mock("@/app/courses/tabs/content/course-content-tab", () => ({ CourseContentTab: () => null }));
vi.mock("@/app/courses/tabs/student-grades-tab", () => ({ StudentGradesTab: () => null }));
vi.mock("@/app/courses/components/course-copy-dialog", () => ({ CourseCopyDialog: () => null }));
vi.mock("@/app/courses/components/enrollment-controls", () => ({ EnrollmentControls: () => null }));
vi.mock("@/app/courses/tabs/assignments/create-assignment-dialog", () => ({ CreateAssignmentDialog: () => null }));

import CourseDetailPage from "./page";

describe("CourseDetailPage", () => {
  it("keeps hooks stable while the course query resolves", () => {
    state.ready = false;
    const view = render(
      <MemoryRouter initialEntries={["/courses/course-1/assignments"]}>
        <Routes>
          <Route path="/courses/:courseId/:tab" element={<CourseDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    state.ready = true;
    expect(() => view.rerender(
      <MemoryRouter initialEntries={["/courses/course-1/assignments"]}>
        <Routes>
          <Route path="/courses/:courseId/:tab" element={<CourseDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )).not.toThrow();

    expect(screen.getByRole("heading", { name: "Biology" })).toBeInTheDocument();
  });
});

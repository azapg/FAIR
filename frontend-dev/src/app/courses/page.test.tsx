import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({ authenticated: false }));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: state.authenticated ? { id: "user-1" } : null,
    isAuthenticated: state.authenticated,
  }),
}));

vi.mock("@/hooks/use-permission", async () => {
  const React = await import("react");
  return {
    usePermission: () => {
      React.useState(null);
      return true;
    },
  };
});

vi.mock("@/hooks/use-courses", () => ({
  useCourses: () => ({ data: [], isPending: false, isError: false }),
  useCreateCourse: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteCourse: () => ({ mutateAsync: vi.fn() }),
  useJoinCourseByCode: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("@/components/breadcrumb-nav", () => ({ BreadcrumbNav: () => null }));
vi.mock("@/app/courses/components/course-grid", () => ({ default: () => null }));
vi.mock("@/app/courses/components/course-form-dialog", () => ({ default: () => null }));

import CoursesPage from "./page";

describe("CoursesPage", () => {
  it("keeps permission hook order stable when authentication resolves", () => {
    state.authenticated = false;
    const view = render(<MemoryRouter><CoursesPage /></MemoryRouter>);

    state.authenticated = true;
    expect(() => view.rerender(<MemoryRouter><CoursesPage /></MemoryRouter>)).not.toThrow();
  });
});

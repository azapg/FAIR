import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Course } from "@/hooks/use-courses";
import { CourseSettingsDialog } from "./course-settings-dialog";

const mutate = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/use-courses", () => ({
  coursesKeys: { all: ["courses"] },
  useUpdateCourse: () => ({ mutate, isPending: false }),
}));
vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("./course-copy-dialog", () => ({
  CourseCopyDialog: () => <button>Copy course</button>,
}));
vi.mock("../tabs/runs-tab", () => ({
  RunsTab: () => <p>Course run history</p>,
}));
vi.mock("../tabs/flows-tab", () => ({
  FlowsTab: () => <p>Course flow editor</p>,
}));
vi.mock("../tabs/capabilities-tab", () => ({
  CapabilitiesTab: () => <p>Available capabilities</p>,
}));
vi.mock("../tabs/artifacts-tab", () => ({
  ArtifactsTab: () => <p>Course artifacts</p>,
}));
const course = {
  id: "course-1",
  name: "Biology",
  description: "Life sciences",
  isArchived: false,
} as Course;
function mount(canEdit = true) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <CourseSettingsDialog
          course={course}
          assignments={[]}
          canEdit={canEdit}
          enrollmentControls={<p>Enrollment controls</p>}
          onClose={() => {}}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
describe("Course settings", () => {
  afterEach(cleanup);
  it("keeps copying and advanced tools in the settings layout", () => {
    mount();
    expect(
      screen.getByRole("button", { name: "Copy course" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Flows" }));
    expect(screen.getByText("Course flow editor")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Runs" }));
    expect(screen.getByText("Course run history")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Enrollment" }));
    expect(screen.getByText("Enrollment controls")).toBeInTheDocument();
  });
  it("saves course details through the existing update action", () => {
    mount();
    fireEvent.change(screen.getByLabelText("Course name"), {
      target: { value: "Advanced Biology" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(mutate).toHaveBeenCalledWith({
      id: "course-1",
      data: { name: "Advanced Biology", description: "Life sciences" },
    });
  });
  it("does not expose owner-only edits or archiving to assistants", () => {
    mount(false);
    expect(screen.getByLabelText("Course name")).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Archive" }),
    ).not.toBeInTheDocument();
  });
});

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => false,
}));

vi.mock("@/hooks/use-flows", () => ({
  latestPublishedVersion: () => undefined,
  useCreateFlow: () => ({ mutateAsync: vi.fn() }),
  useFlows: () => ({ data: [], isLoading: false }),
  useStartFlow: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/use-submissions", () => ({
  useSubmissions: () => ({ data: [] }),
}));

import { FlowsSidebar } from "./flows-sidebar";
import { FlowSidebarProvider } from "@/components/ui/sidebar";

afterEach(cleanup);

describe("FlowsSidebar", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("exposes the resizable rail for the flow sidebar", () => {
    render(
      <FlowSidebarProvider
        cookieName="flow_sidebar_state"
        width="22rem"
        resizable
        minWidth={288}
        maxWidth={512}
      >
        <FlowsSidebar
          side="right"
          courseId="course-1"
          assignmentId="assignment-1"
        />
      </FlowSidebarProvider>,
    );

    const rail = screen.getByRole("separator", {
      name: "Resize or toggle sidebar",
    });
    expect(rail).toHaveAttribute("aria-valuenow", "352");

    fireEvent.keyDown(rail, { key: "ArrowRight" });

    expect(rail).toHaveAttribute("aria-valuenow", "344");
    expect(window.localStorage.getItem("flow_sidebar_state_width")).toBe("344");
  });
});

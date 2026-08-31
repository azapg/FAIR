import { render, screen } from "@testing-library/react";
import { Plus } from "lucide-react";
import { describe, expect, it, vi } from "vitest";

import { FloatingActionButton, FloatingNav } from "./floating-nav";

describe("FloatingNav", () => {
  it("renders one right-aligned action with a high-contrast icon color", () => {
    const { container } = render(
      <FloatingNav
        items={[]}
        value=""
        onValueChange={vi.fn()}
        action={<FloatingActionButton aria-label="Add"><span>+</span></FloatingActionButton>}
      />,
    );

    expect(screen.getAllByRole("button", { name: "Add" })).toHaveLength(1);
    expect(container.firstElementChild).toHaveClass("justify-end");
    expect(screen.getByRole("button", { name: "Add" })).toHaveClass("text-foreground");
  });

  it("gives the view group the available width before the standalone action", () => {
    const { container } = render(
      <FloatingNav
        items={[{ value: "timeline", label: "Timeline", icon: Plus }]}
        value="timeline"
        onValueChange={vi.fn()}
        action={<FloatingActionButton aria-label="Create"><span>+</span></FloatingActionButton>}
      />,
    );

    const navigation = screen.getByRole("navigation", { name: "Views" });
    const action = screen.getByRole("button", { name: "Create" });
    expect(navigation.nextElementSibling).toBe(action);
    expect(navigation).toHaveClass("flex-1");
    expect(container.firstElementChild).toHaveClass("justify-end");
  });

  it("centers the view group when there is no standalone action", () => {
    const { container } = render(
      <FloatingNav
        items={[{ value: "timeline", label: "Timeline", icon: Plus }]}
        value="timeline"
        onValueChange={vi.fn()}
      />,
    );

    expect(container.firstElementChild).toHaveClass("justify-center");
    expect(container.querySelector('[aria-label="Views"]')).toHaveClass("w-full", "max-w-md");
  });
});

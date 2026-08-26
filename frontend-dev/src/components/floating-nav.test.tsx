import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FloatingActionButton, FloatingNav } from "./floating-nav";

describe("FloatingNav", () => {
  it("renders one left-aligned action with a high-contrast icon color", () => {
    const { container } = render(
      <FloatingNav
        items={[]}
        value=""
        onValueChange={vi.fn()}
        action={<FloatingActionButton aria-label="Add"><span>+</span></FloatingActionButton>}
      />,
    );

    expect(screen.getAllByRole("button", { name: "Add" })).toHaveLength(1);
    expect(container.firstElementChild).toHaveClass("justify-start");
    expect(screen.getByRole("button", { name: "Add" })).toHaveClass("text-foreground");
  });
});

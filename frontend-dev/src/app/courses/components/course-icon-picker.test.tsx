import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CourseIconPicker } from "./course-icon-picker";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

afterEach(cleanup);

describe("CourseIconPicker", () => {
  it("searches the curated metadata and selects an icon", () => {
    const onValueChange = vi.fn();
    render(<CourseIconPicker value="book-open" onValueChange={onValueChange} />);

    fireEvent.click(screen.getByRole("button", { name: /courses\.icons\.book-open/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "courses.searchIcons" }), {
      target: { value: "química" },
    });
    fireEvent.click(screen.getByRole("button", { name: "courses.icons.chemistry" }));

    expect(onValueChange).toHaveBeenCalledWith("chemistry");
  });

  it("shows an empty state for unmatched searches", () => {
    render(<CourseIconPicker value="book-open" onValueChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /courses\.icons\.book-open/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "courses.searchIcons" }), {
      target: { value: "not-a-real-subject" },
    });

    expect(screen.getByText("common.noResults")).toBeInTheDocument();
  });
});

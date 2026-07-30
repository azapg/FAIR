import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useCreateAssignment } = vi.hoisted(() => ({
  useCreateAssignment: vi.fn(),
}));

vi.mock("@/hooks/use-assignments", () => ({
  useCreateAssignment,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => ({
      "common.add": "Add",
      "common.create": "Create",
      "assignments.addResources": "Add resources",
      "assignments.creating": "Creating",
      "assignments.description": "Description",
      "assignments.descriptionPlaceholder": "Describe the assignment",
      "assignments.dueDate": "Due date",
      "assignments.newAssignment": "New Assignment",
      "assignments.resources": "Resources",
      "assignments.titleLabel": "Title",
      "assignments.titlePlaceholder": "Assignment title",
      "assignments.totalPoints": "Total points",
    })[key] ?? key,
  }),
}));

import { CreateAssignmentDialog } from "./create-assignment-dialog";

describe("CreateAssignmentDialog", () => {
  beforeEach(() => {
    useCreateAssignment.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn(),
    });
  });

  it("keeps the create footer outside the scrollable form body", () => {
    render(
      <CreateAssignmentDialog
        courseId="course-1"
        onAssignmentCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "New Assignment" });
    const scrollArea = dialog.querySelector<HTMLElement>('[data-slot="scroll-area"]');
    const footer = dialog.querySelector<HTMLElement>('[data-slot="dialog-footer"]');

    expect(dialog).toHaveClass("max-h-[calc(100vh-2rem)]");
    expect(scrollArea).toHaveClass("min-h-0", "flex-1");
    expect(footer).toBeInTheDocument();
    expect(scrollArea).not.toContainElement(footer);
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });
});

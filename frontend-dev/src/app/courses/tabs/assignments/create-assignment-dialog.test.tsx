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
      "common.cancel": "Cancel",
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

  it("keeps the actions outside a natively scrollable form body", () => {
    render(
      <CreateAssignmentDialog
        courseId="course-1"
        onAssignmentCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "New Assignment" });
    const scrollBody = dialog.querySelector<HTMLElement>('[data-slot="assignment-form-scroll"]');
    const footer = dialog.querySelector<HTMLElement>('[data-slot="dialog-footer"]');
    const description = screen.getByLabelText("Description");

    expect(dialog).toHaveClass("max-h-[calc(100dvh-2rem)]");
    expect(scrollBody).toHaveClass("min-h-0", "flex-1", "overflow-y-auto");
    expect(description).toHaveClass("max-h-64", "overflow-y-auto");
    expect(footer).toBeInTheDocument();
    expect(scrollBody).not.toContainElement(footer);
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
  });
});

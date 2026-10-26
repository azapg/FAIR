import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mutations = vi.hoisted(() => ({
  remove: vi.fn(),
  updateRole: vi.fn(),
}));

vi.mock("@/hooks/use-courses", () => ({
  useCourseEnrollments: () => ({
    data: [
      {
        id: "assistant-enrollment",
        userId: "assistant-user",
        courseId: "course-1",
        role: "assistant",
        status: "active",
        userName: "Alex Assistant",
        userEmail: "alex@example.com",
      },
    ],
    isLoading: false,
  }),
  useRemoveEnrollment: () => ({ mutate: mutations.remove }),
  useUpdateEnrollmentRole: () => ({ mutate: mutations.updateRole }),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { ParticipantsTab } from "./participants-tab";

describe("ParticipantsTab", () => {
  beforeEach(() => {
    mutations.remove.mockClear();
    mutations.updateRole.mockClear();
  });

  it("lets a course owner demote and remove an assistant", () => {
    render(
      <ParticipantsTab
        courseId="course-1"
        instructor={{
          id: "owner-user",
          name: "Course Owner",
          email: "owner@example.com",
          role: "owner",
        }}
        canManageRoles
      />,
    );

    const actionButtons = screen.getAllByRole("button");
    fireEvent.pointerDown(actionButtons[1], { button: 0, ctrlKey: false });
    fireEvent.click(screen.getByText("Make student"));

    expect(mutations.updateRole).toHaveBeenCalledWith({
      id: "assistant-enrollment",
      role: "student",
    });

    fireEvent.pointerDown(actionButtons[1], { button: 0, ctrlKey: false });
    fireEvent.click(screen.getByText("Remove from course"));

    expect(mutations.remove).toHaveBeenCalledWith("assistant-enrollment");
  });
});

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const testState = vi.hoisted(() => ({
  isMobile: false,
  returnSubmission: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "submissions.attachments": "Attachments",
        "submissions.closeDetails": "Close submission details",
        "submissions.detailsDescription":
          "Review the submission, grade it, leave feedback, and view its activity.",
        "submissions.expandDetails": "Expand submission details",
        "submissions.feedback": "Feedback",
        "submissions.grade": "Grade",
        "submissions.moreActions": "More submission actions",
        "submissions.noAttachments": "No attachments",
        "submissions.privateComments": "Private comments",
        "submissions.returnAction": "Return",
        "submissions.status": "Status",
        "submissions.timeline": "Timeline",
        "submissions.turnedIn": "Turned in",
      })[key] ?? key,
    i18n: { language: "en" },
  }),
}));

vi.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => testState.isMobile,
}));

vi.mock("@/hooks/use-submissions", () => ({
  hasUnpublishedDraft: () => true,
  useReturnSubmission: () => ({
    isPending: false,
    mutate: testState.returnSubmission,
  }),
  useSubmissionTimeline: () => ({ data: [] }),
}));

vi.mock("./submissions", () => ({
  formatShortDate: () => "Jul 27, 2026",
  InlineEditableFeedback: ({ startInEditMode }: { startInEditMode?: boolean }) => (
    <div data-testid="feedback" data-editing={String(Boolean(startInEditMode))} />
  ),
  InlineEditableScore: () => <div>91</div>,
  SubmissionStatusLabel: () => <div>Graded</div>,
}));

vi.mock("@/components/submission-timeline", () => ({
  default: () => <div>Submission timeline</div>,
}));

vi.mock("@/components/submission-comments", () => ({
  SubmissionComments: () => <div>Submission comments</div>,
}));

import type { Submission } from "@/hooks/use-submissions";
import { SubmissionSheet } from "./submission-sheet";

const submission = {
  id: "submission-1",
  assignmentId: "assignment-1",
  submitterId: "submitter-1",
  submitter: {
    id: "submitter-1",
    name: "Ada Student",
    email: "ada@example.edu",
    role: "student",
  },
  submittedAt: "2026-07-27T12:00:00Z",
  status: "graded",
  artifacts: [],
  attemptNumber: 1,
  isLate: false,
  draftScore: 91,
  draftFeedback: "Strong work",
} satisfies Submission;

afterEach(cleanup);

describe("SubmissionSheet", () => {
  beforeEach(() => {
    testState.isMobile = false;
    testState.returnSubmission.mockReset();
  });

  it.each([
    { viewport: "desktop", isMobile: false, direction: "right" },
    { viewport: "mobile", isMobile: true, direction: "bottom" },
  ])("uses a responsive $viewport Vaul drawer from the $direction", ({
    isMobile,
    direction,
  }) => {
    testState.isMobile = isMobile;

    render(
      <SubmissionSheet
        submission={submission}
        open
        onOpenChange={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "Ada Student" });
    expect(dialog).toHaveAttribute("data-vaul-drawer-direction", direction);
    expect(dialog).toHaveClass("h-9/10", "w-full");
    if (isMobile) {
      expect(dialog).toHaveClass(
        "data-[vaul-drawer-direction=bottom]:max-h-[90vh]",
      );
    } else {
      expect(dialog).toHaveClass("md:min-w-4/5", "lg:min-w-1/2");
    }
    expect(dialog).toHaveAccessibleDescription(
      "Review the submission, grade it, leave feedback, and view its activity.",
    );
  });

  it("closes through the drawer control and keeps submission actions working", () => {
    const onOpenChange = vi.fn();

    render(
      <SubmissionSheet
        submission={submission}
        open
        onOpenChange={onOpenChange}
        focusOn="feedback"
      />,
    );

    expect(screen.getByTestId("feedback")).toHaveAttribute(
      "data-editing",
      "true",
    );

    fireEvent.click(screen.getByRole("button", { name: "Return" }));
    expect(testState.returnSubmission).toHaveBeenCalledWith("submission-1");

    fireEvent.click(
      screen.getByRole("button", { name: "Close submission details" }),
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

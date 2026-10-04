import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      key === "submissions.grade" ? "Grade" : "Feedback",
  }),
}));

import { Submission } from "@/hooks/use-submissions";
import { StudentSubmissionGrade } from "./student-submission-grade";

afterEach(cleanup);

const submission = {
  id: "submission-1",
  assignmentId: "assignment-1",
  submitterId: "submitter-1",
  submittedAt: "2026-07-27T12:00:00Z",
  status: "returned",
  artifacts: [],
  attemptNumber: 1,
  isLate: false,
} satisfies Submission;

describe("StudentSubmissionGrade", () => {
  it("shows the published grade and feedback returned to the student", () => {
    render(
      <StudentSubmissionGrade
        submission={{
          ...submission,
          draftScore: null,
          draftFeedback: null,
          publishedScore: 91,
          publishedFeedback: "Clear argument",
          returnedAt: "2026-07-27T13:00:00Z",
        }}
      />,
    );

    expect(screen.getByTestId("published-grade")).toHaveTextContent("91");
    expect(screen.getByTestId("published-feedback")).toHaveTextContent(
      "Clear argument",
    );
  });

  it("does not expose an unreturned draft result", () => {
    const { container } = render(
      <StudentSubmissionGrade
        submission={{
          ...submission,
          status: "graded",
          draftScore: 88,
          draftFeedback: "Draft feedback",
        }}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});

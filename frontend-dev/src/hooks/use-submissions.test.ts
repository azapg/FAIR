import { describe, expect, it } from "vitest";

import { hasUnpublishedDraft, Submission } from "./use-submissions";

const submission = {
  id: "submission-1",
  assignmentId: "assignment-1",
  submitterId: "submitter-1",
  submittedAt: "2026-07-27T12:00:00Z",
  status: "returned",
  artifacts: [],
  attemptNumber: 1,
  isLate: false,
  draftScore: 90,
  draftFeedback: "Good work",
  publishedScore: 90,
  publishedFeedback: "Good work",
} satisfies Submission;

describe("hasUnpublishedDraft", () => {
  it("is false immediately after a draft is returned", () => {
    expect(hasUnpublishedDraft(submission)).toBe(false);
  });

  it("is true when an instructor changes a returned grade", () => {
    expect(
      hasUnpublishedDraft({
        ...submission,
        draftScore: 95,
      }),
    ).toBe(true);
  });

  it("is true when an instructor changes returned feedback", () => {
    expect(
      hasUnpublishedDraft({
        ...submission,
        draftFeedback: "Excellent revision",
      }),
    ).toBe(true);
  });
});

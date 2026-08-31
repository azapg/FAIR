import { useTranslation } from "react-i18next";

import { Submission } from "@/hooks/use-submissions";

export function StudentSubmissionGrade({
  submission,
}: {
  submission: Submission;
}) {
  const { t } = useTranslation();
  const hasPublishedResult =
    submission.returnedAt != null ||
    submission.publishedScore != null ||
    submission.publishedFeedback != null;

  if (!hasPublishedResult) return null;

  return (
    <dl className="mb-3 grid gap-2 rounded-md border bg-background p-3">
      <div className="flex items-baseline justify-between gap-4">
        <dt className="font-medium">{t("submissions.grade")}</dt>
        <dd data-testid="published-grade">
          {submission.publishedScore ?? "—"}
        </dd>
      </div>
      {submission.publishedFeedback != null &&
        submission.publishedFeedback !== "" && (
          <div className="space-y-1">
            <dt className="font-medium">{t("submissions.feedback")}</dt>
            <dd
              className="whitespace-pre-wrap text-muted-foreground"
              data-testid="published-feedback"
            >
              {submission.publishedFeedback}
            </dd>
          </div>
        )}
    </dl>
  );
}

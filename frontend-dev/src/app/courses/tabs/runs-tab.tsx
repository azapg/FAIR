import {useMemo} from "react";
import {Link} from "react-router-dom";
import {useTranslation} from "react-i18next";
import {Assignment} from "@/hooks/use-assignments";
import {Submission, useDeleteSubmission, useSubmissions} from "@/hooks/use-submissions";
import {SubmissionStatusLabel} from "@/app/assignment/components/submissions/submissions";
import {Button} from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";

export function RunsTab({
  courseId,
  assignments,
}: {
  courseId?: string;
  assignments: Assignment[];
}) {
  const {t} = useTranslation();
  const {data: submissions, isLoading, isError, refetch} = useSubmissions();
  const deleteSubmission = useDeleteSubmission();

  const assignmentNames = useMemo(() => {
    const map = new Map<string, string>();
    assignments?.forEach((a) => map.set(a.id, a.title));
    return map;
  }, [assignments]);

  const courseSubmissions: Submission[] = useMemo(() => {
    if (!submissions) return [];
    return submissions.filter(sub => assignmentNames.has(sub.assignmentId));
  }, [submissions, assignmentNames]);

  if (!courseId) {
    return <div className="text-sm text-muted-foreground">{t("runs.noCourse")}</div>;
  }

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError) {
    return <div>{t("runs.errorLoading")}</div>;
  }

  if (!courseSubmissions.length) {
    return <div className="text-sm text-muted-foreground">{t("runs.empty")}</div>;
  }

  const handleDelete = async (submissionId: string) => {
    await deleteSubmission.mutateAsync(submissionId);
    await refetch();
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("runs.title")}</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("runs.assignment")}</TableHead>
            <TableHead>{t("runs.submitter")}</TableHead>
            <TableHead>{t("runs.status")}</TableHead>
            <TableHead>{t("runs.runId")}</TableHead>
            <TableHead>{t("runs.submittedAt")}</TableHead>
            <TableHead className="text-right">{t("actions.courseActions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {courseSubmissions.map((submission) => {
            const assignmentTitle = assignmentNames.get(submission.assignmentId) ?? submission.assignmentId;
            const submitted = submission.submittedAt
              ? new Date(submission.submittedAt).toLocaleString()
              : "—";
            return (
              <TableRow key={submission.id}>
                <TableCell>
                  {courseId ? (
                    <Button variant="link" asChild className="p-0 h-auto font-normal">
                      <Link to={`/courses/${courseId}/assignments/${submission.assignmentId}`}>
                        {assignmentTitle}
                      </Link>
                    </Button>
                  ) : (
                    assignmentTitle
                  )}
                </TableCell>
                <TableCell>{submission.submitter?.name ?? "—"}</TableCell>
                <TableCell><SubmissionStatusLabel status={submission.status}/></TableCell>
                <TableCell className="font-mono text-xs">{submission.officialRunId ?? "—"}</TableCell>
                <TableCell>{submitted}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(submission.id)}
                  >
                    {t("common.delete")}
                  </Button>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  );
}

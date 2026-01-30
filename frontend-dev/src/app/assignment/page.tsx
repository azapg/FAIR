import { Button } from "@/components/ui/button";
import {
  ArrowUpRight,
  CircleCheck,
  FileText,
  Hourglass,
  Plus,
} from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { SubmissionsTable } from "@/app/assignment/components/submissions/submissions-table";
import { useSubmissionColumns } from "@/app/assignment/components/submissions/submissions";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { WorkflowsSidebar } from "@/app/assignment/components/sidebar/workflows-sidebar";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import { MarkdownRenderer } from "@/components/markdown-renderer";

import { useParams } from "react-router-dom";
import { useAssignment } from "@/hooks/use-assignments";
import { useCourse } from "@/hooks/use-courses";
import { useWorkflowStore } from "@/store/workflows-store";
import { useWorkflows } from "@/hooks/use-workflows";
import { useEffect } from "react";
import { CreateSubmissionDialog } from "@/app/assignment/components/submissions/create-submission-dialog";
import { useArtifacts } from "@/hooks/use-artifacts";
import { useSubmissions } from "@/hooks/use-submissions";
import { useTranslation } from "react-i18next";

export default function AssignmentPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const { data: assignment, isLoading, isError } = useAssignment(assignmentId!);
  // TODO: This is ugly, try getting courseId from somewhere else, maybe from parents
  const { data: course } = useCourse(assignment?.courseId!);
  const setActiveCourseId = useWorkflowStore(
    (state) => state.setActiveCourseId,
  );
  const { isLoading: isLoadingWorkflows } = useWorkflows();
  const {
    data: artifacts,
    isLoading: isLoadingArtifacts,
    isError: isErrorArtifacts,
  } = useArtifacts({
    assignmentId: assignmentId,
  });
  const {
    data: submissions,
    isLoading: isLoadingSubmissions,
    isError: isErrorSubmissions,
  } = useSubmissions({
    assignment_id: assignmentId,
  });
  const { t } = useTranslation();

  const isOverallLoading =
    isLoading ||
    isLoadingWorkflows ||
    isLoadingArtifacts ||
    isLoadingSubmissions;

  const columns = useSubmissionColumns();

  useEffect(() => {
    if (course?.id) {
      setActiveCourseId(course.id);
    }
  }, [course]);

  if (isOverallLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (
    isError ||
    !assignment ||
    !course ||
    isErrorArtifacts ||
    isErrorSubmissions
  ) {
    return <div>{t("errors.errorLoadingAssignment")}</div>;
  }

  return (
    <SidebarProvider
      className={"flex flex-row m-0 p-0 h-auto overflow-none"}
      cookieName="workflow_sidebar_state"
      keyboardShortcut="m"
    >
      <div className={"w-full h-full overflow-auto break-words"}>
        <div className={"flex flex-row justify-between items-center py-2 px-5"}>
          <BreadcrumbNav
            segments={[
              {
                label: t("courses.title"),
                slug: "courses",
              },
              {
                label: course?.name || assignment?.courseId.toLocaleString(),
                slug:
                  course?.id.toLocaleString() ||
                  assignment?.courseId.toLocaleString(),
              },
              {
                label: t("tabs.assignments"),
                slug: "assignments",
              },
              {
                label: assignment.title,
                slug: assignment.id.toLocaleString(),
              },
            ]}
          />
          <SidebarTrigger />
        </div>
        <Separator />
        <div className={"px-8 pt-5"}>
          <div className={"mb-5"}>
            <h1 className={"text-3xl font-bold pb-1"}>{assignment.title}</h1>
            <MarkdownRenderer className={"text-sm text-muted-foreground"}>
              {assignment.description}
            </MarkdownRenderer>

            <ScrollArea className={"w-full h-auto"}>
              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>
                  {t("properties.title")}
                </h2>
                <Button variant={"secondary"} size={"sm"}>
                  <CircleCheck /> {t("properties.completed")}
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Hourglass />{" "}
                  {assignment.deadline
                    ? new Date(assignment.deadline).toLocaleDateString(
                        undefined,
                        {
                          day: "2-digit",
                          month: "short",
                        },
                      )
                    : t("common.noDeadline")}
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Plus />
                </Button>
              </div>

              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>
                  {t("assignments.resources")}
                </h2>
                {artifacts && artifacts.length > 0 ? (
                  artifacts.map((artifact) => (
                    <Button key={artifact.id} variant={"secondary"} size={"sm"}>
                      <FileText />
                      {artifact.title}
                      <ArrowUpRight className="text-muted-foreground" />
                    </Button>
                  ))
                ) : (
                  <></>
                )}
                <Button variant={"ghost"} size={"sm"}>
                  <Plus />
                </Button>
              </div>

              <ScrollBar orientation="horizontal" />
            </ScrollArea>
          </div>

          <div className={"space-y-3 mb-5"}>
            <div className={"flex justify-between items-center mb-3"}>
              <h2 className={"text-xl font-semibold"}>{t("submissions.title")}</h2>
              <CreateSubmissionDialog assignmentId={assignment.id.toString()} />
            </div>
            <SubmissionsTable columns={columns} data={submissions ?? []} />
          </div>
        </div>
      </div>
      <WorkflowsSidebar side={"right"} className={"pt-16"} assignmentId={assignmentId ?? ""} />
    </SidebarProvider>
  );
}

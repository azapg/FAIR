import { Button } from "@/components/ui/button";
import {
  ArrowUpRight,
  FileText,
  Hourglass,
  Plus,
} from "lucide-react";
import { SubmissionsTable } from "@/app/assignment/components/submissions/submissions-table";
import { useSubmissionColumns } from "@/app/assignment/components/submissions/submissions";
import { WorkflowsSidebarProvider, WorkflowsSidebarTrigger } from "@/components/ui/sidebar";
import { WorkflowsSidebar } from "@/app/assignment/components/sidebar/workflows-sidebar";
import {
  PropertiesDisplay,
  Property,
  PropertyLabel,
  PropertyValue,
} from "@/components/properties-display";

import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import { MarkdownRenderer } from "@/components/markdown-renderer";

import { useParams } from "react-router-dom";
import { useAssignment } from "@/hooks/use-assignments";
import { useCourse } from "@/hooks/use-courses";
import { useWorkflowStore } from "@/store/workflows-store";
import { useWorkflows } from "@/hooks/use-workflows";
import { useEffect, useState } from "react";
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
  const [isCreateSubmissionOpen, setIsCreateSubmissionOpen] = useState(false);

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
    <WorkflowsSidebarProvider
      cookieName="workflow_sidebar_state"
      keyboardShortcut="m"
      width="22rem"
      widthMobile="18rem"
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
          <WorkflowsSidebarTrigger />
        </div>
        <div className={"px-8 pt-2"}>
          <div className={"mb-5"}>
            <h1 className={"text-3xl font-bold pb-1"}>{assignment.title}</h1>
            <MarkdownRenderer className={"text-sm text-muted-foreground"}>
              {assignment.description}
            </MarkdownRenderer>

            <PropertiesDisplay scroll>
                <Property>
                  <PropertyLabel>{t("properties.title")}</PropertyLabel>
                  <PropertyValue className="flex flex-row gap-1 items-center">
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
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>{t("assignments.resources")}</PropertyLabel>
                  <PropertyValue className="flex flex-row gap-1 items-center">
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
                  </PropertyValue>
                </Property>
            </PropertiesDisplay>
          </div>

          <div className={"space-y-3 mb-5"}>
            <div className={"flex justify-between items-center mb-3"}>
              <h2 className={"text-xl font-semibold"}>{t("submissions.title")}</h2>
              <Button size="sm" onClick={() => setIsCreateSubmissionOpen(true)}>
                <Plus /> {t("common.add")}
              </Button>
            </div>
            <SubmissionsTable columns={columns} data={submissions ?? []} onCreateSubmission={() => setIsCreateSubmissionOpen(true)}
            />
            <CreateSubmissionDialog
              assignmentId={assignment.id.toString()}
              open={isCreateSubmissionOpen}
              onOpenChange={setIsCreateSubmissionOpen}
            />
          </div>
        </div>
      </div>
      <WorkflowsSidebar side={"right"} assignmentId={assignmentId ?? ""} />
    </WorkflowsSidebarProvider>
  );
}

import { Button } from "@/components/ui/button";
import { FileText, Hourglass, Plus } from "lucide-react";
import { SubmissionsTable } from "@/app/assignment/components/submissions/submissions-table";
import { useSubmissionColumns } from "@/app/assignment/components/submissions/submissions";
import {
  WorkflowsSidebarProvider,
  WorkflowsSidebarTrigger,
} from "@/components/ui/sidebar";
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
import { useAssignment, Assignment } from "@/hooks/use-assignments";
import { useCourse } from "@/hooks/use-courses";
import { useWorkflowStore } from "@/store/workflows-store";
import { useWorkflows } from "@/hooks/use-workflows";
import { useEffect, useState } from "react";
import { CreateSubmissionDialog } from "@/app/assignment/components/submissions/create-submission-dialog";
import { useArtifacts } from "@/hooks/use-artifacts";
import { useSubmissions, Submission } from "@/hooks/use-submissions";
import { useTranslation } from "react-i18next";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArtifactAction } from "@/components/artifact-action";
import { useAuth } from "@/contexts/auth-context";
import { usePermission } from "@/hooks/use-permission";

interface InstructorSubmissionsSectionProps {
  setIsCreateSubmissionOpen: (value: boolean) => void;
  isCreateSubmissionOpen: boolean;
  submissions: Submission[] | undefined;
  columns: any;
  assignment: Assignment;
}

function InstructorSubmissionsSection({
  setIsCreateSubmissionOpen,
  isCreateSubmissionOpen,
  submissions,
  columns,
  assignment,
}: InstructorSubmissionsSectionProps) {
  const { t } = useTranslation();

  return (
    <div className={"space-y-3 mb-5"}>
      <div className={"flex justify-between items-center mb-3"}>
        <h2 className={"text-xl font-semibold"}>{t("submissions.title")}</h2>
        <Button size="sm" onClick={() => setIsCreateSubmissionOpen(true)}>
          <Plus /> {t("common.add")}
        </Button>
      </div>
      <SubmissionsTable
        columns={columns}
        data={submissions ?? []}
        canManage={true}
        onCreateSubmission={() => setIsCreateSubmissionOpen(true)}
      />
      <CreateSubmissionDialog
        assignmentId={assignment.id.toString()}
        open={isCreateSubmissionOpen}
        onOpenChange={setIsCreateSubmissionOpen}
      />
    </div>
  );
}

export default function AssignmentPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const { data: assignment, isLoading, isError } = useAssignment(assignmentId!);
  const { data: course } = useCourse(
    assignment?.courseId,
    Boolean(assignment?.courseId),
  );
  const { user } = useAuth();
  // TODO: This is ugly. We have to normalize the API. Even if it's not detailed,
  // we should send course.instructor.id instead of having two different shapes
  //  for the same data depending on the endpoint.
  const instructorId = course
    ? "instructorId" in course
      ? course.instructorId
      : course.instructor.id
    : undefined;
  const canManageUsers = usePermission("manage_users");
  const canManageAssignmentUi =
    !!user && !!course && (instructorId === user.id || canManageUsers);
  const setActiveCourseId = useWorkflowStore(
    (state) => state.setActiveCourseId,
  );
  const { isLoading: isLoadingWorkflows } = useWorkflows(canManageAssignmentUi);
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

  const columns = useSubmissionColumns(canManageAssignmentUi);

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

  const isCourseOwner = !!user && instructorId === user.id;
  const isInstructorView = isCourseOwner || canManageUsers;

  return (
    <WorkflowsSidebarProvider
      cookieName="workflow_sidebar_state"
      keyboardShortcut="m"
      width="22rem"
      widthMobile="18rem"
    >
      <ScrollArea className="w-full h-svh flex-1 min-w-0">
        <div className="min-w-0 break-words">
          <div
            className={"flex flex-row justify-between items-center py-2 px-5"}
          >
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
            {isInstructorView && <WorkflowsSidebarTrigger />}
          </div>
          <div className={"px-8 pt-2"}>
            <div className={"mb-5"}>
              <h1 className={"text-3xl font-bold pb-1"}>{assignment.title}</h1>
              {!assignment.description ||
              assignment.description.trim() === "" ? (
                <p className="text-muted-foreground italic">
                  {t("assignments.noDescription")}
                </p>
              ) : (
                <MarkdownRenderer
                  className={"text-sm text-muted-foreground"}
                  clamp
                >
                  {assignment.description}
                </MarkdownRenderer>
              )}

              <PropertiesDisplay scroll className="items-start pt-3">
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
                    {isInstructorView && (
                      <Button variant={"ghost"} size={"sm"}>
                        <Plus />
                      </Button>
                    )}
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>{t("assignments.resources")}</PropertyLabel>
                  <PropertyValue className="flex flex-row gap-1 items-center">
                    {artifacts && artifacts.length > 0 ? (
                      artifacts.map((artifact) => (
                        <ArtifactAction
                          key={artifact.id}
                          artifact={artifact}
                          icon={FileText}
                          variant="secondary"
                          size="sm"
                        />
                      ))
                    ) : (
                      <></>
                    )}
                    {isInstructorView && (
                      <Button variant={"ghost"} size={"sm"}>
                        <Plus />
                      </Button>
                    )}
                  </PropertyValue>
                </Property>
              </PropertiesDisplay>
            </div>

            {isInstructorView && (
              <InstructorSubmissionsSection
                setIsCreateSubmissionOpen={setIsCreateSubmissionOpen}
                isCreateSubmissionOpen={isCreateSubmissionOpen}
                submissions={submissions}
                columns={columns}
                assignment={assignment}
              />
            )}
          </div>
        </div>
      </ScrollArea>
      {isInstructorView && (
        <WorkflowsSidebar side={"right"} assignmentId={assignmentId ?? ""} />
      )}
    </WorkflowsSidebarProvider>
  );
}

import {Button} from "@/components/ui/button";
import {ArrowUpRight, CircleCheck, ExternalLink, FileText, Hourglass, MoveUpRight, Plus} from "lucide-react";
import {Separator} from "@/components/ui/separator";
import {SubmissionsTable} from "@/app/assignment/components/submissions/submissions-table";
import {columns} from "@/app/assignment/components/submissions/submissions";
import {SidebarProvider, SidebarTrigger} from "@/components/ui/sidebar";
import {WorkflowsSidebar} from "@/app/assignment/components/sidebar/workflows-sidebar";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import {BreadcrumbNav} from "@/components/breadcrumb-nav";
import {MarkdownRenderer} from "@/components/markdown-renderer";

import {useParams} from "react-router-dom";
import {useAssignment} from "@/hooks/use-assignments";
import {useCourse} from "@/hooks/use-courses";
import {useWorkflowStore} from "@/store/workflows-store";
import {useEffect} from "react";
import {CreateSubmissionDialog} from "@/app/assignment/components/submissions/create-submission-dialog";
import { useArtifacts } from "@/hooks/use-artifacts";


export default function AssignmentPage() {
  const {assignmentId} = useParams<{ assignmentId: string }>()
  const {data: assignment, isLoading, isError} = useAssignment(assignmentId!);
  // TODO: This is ugly, try getting course_id from somewhere else, maybe from parents
  const {data: course} = useCourse(assignment?.course_id!);
  const setActiveCourseId = useWorkflowStore(state => state.setActiveCourseId)
  const loadWorkflows = useWorkflowStore(state => state.loadWorkflows)
  const isLoadingWorkflows = useWorkflowStore(state => state.isLoadingWorkflows)
  const workflows = useWorkflowStore(state => state.workflows)
  const {data: artifacts, isLoading: isLoadingArtifacts, isError: isErrorArtifacts, error: errorArtifacts} = useArtifacts({
      assignmentId: assignmentId
    });

  const isOverallLoading = isLoading || isLoadingWorkflows || !workflows || isLoadingArtifacts;

  useEffect(() => {
    if (course?.id) {
      setActiveCourseId(course.id.toString());
      loadWorkflows().then().catch(err => {
        console.error(err)
      });
    }
  }, [course, setActiveCourseId]);

  if (isOverallLoading) {
    return <div>Loading...</div>
  }

  if (isError || !assignment || !course || isErrorArtifacts) {
    return <div>Error loading assignment.</div>
  }


  return (
    <SidebarProvider className={"flex flex-row m-0 p-0 h-auto overflow-none"}>
      <div className={"w-full h-full overflow-auto break-words"}>
        <div className={"flex flex-row justify-between items-center py-2 px-5"}>
          <BreadcrumbNav baseUrl={"demo"} segments={[{
            label: "Courses",
            slug: "courses"
          }, {
            label: course?.name || assignment?.course_id.toLocaleString(),
            slug: course?.id.toLocaleString() || assignment?.course_id.toLocaleString()
          }, {
            label: "Assignments",
            slug: "assignments"
          }, {
            label: assignment.title,
            slug: assignment.id.toLocaleString()
          }]}/>
          <SidebarTrigger/>
        </div>
        <Separator/>
        <div className={"px-8 pt-5"}>
          <div className={"mb-5"}>
            <h1 className={"text-3xl font-bold pb-1"}>{assignment.title}</h1>
            <MarkdownRenderer className={"text-sm text-muted-foreground"}>{assignment.description}</MarkdownRenderer>

            <ScrollArea className={"w-full h-auto"}>
              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>Properties</h2>
                <Button variant={"secondary"} size={"sm"}>
                  <CircleCheck/> Completed
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Hourglass/> {assignment.deadline ? new Date(assignment.deadline).toLocaleDateString(undefined, {
                  day: '2-digit',
                  month: 'short'
                }) : 'No deadline'}
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Plus/>
                </Button>
              </div>

              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>Resources</h2>
                {
                  artifacts && artifacts.length > 0 ? (
                    artifacts.map(artifact => (
                      <Button key={artifact.id} variant={"secondary"} size={"sm"}>
                        <FileText />
                        {artifact.title}
                          <ArrowUpRight className="text-muted-foreground"/>
                      </Button>
                    ))
                  ) : (
                    <></>
                  )}
                <Button variant={"ghost"} size={"sm"}>
                  <Plus/>
                </Button>
              </div>

              <ScrollBar orientation="horizontal"/>
            </ScrollArea>

          </div>

          <div className={"space-y-3 mb-5"}>
            <div className={"flex justify-between items-center mb-3"}>
              <h2 className={"text-xl font-semibold"}>Submissions</h2>
              <CreateSubmissionDialog assignmentId={assignment.id.toString()}/>
            </div>
            <SubmissionsTable columns={columns} data={[]}/>
          </div>

        </div>
      </div>
      <WorkflowsSidebar side={"right"} className={"pt-16"}/>
    </SidebarProvider>
  );
}
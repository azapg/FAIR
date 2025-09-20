import {Button} from "@/components/ui/button";
import {CircleCheck, FileText, Hourglass, Link as LinkIcon, Plus} from "lucide-react";
import {Separator} from "@/components/ui/separator";
import {SubmissionsTable} from "@/app/assignment/components/submissions/submissions-table";
import {columns} from "@/app/assignment/components/submissions/submissions";
import {SidebarProvider, SidebarTrigger} from "@/components/ui/sidebar";
import {WorkflowsSidebar} from "@/app/assignment/components/workflows-sidebar";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import {BreadcrumbNav} from "@/components/breadcrumb-nav";

import {useParams} from "react-router-dom";
import { useAssignment } from "@/hooks/use-assignments";
import { useCourse } from "@/hooks/use-courses";


export default function AssignmentPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const { data: assignment, isLoading, isError } = useAssignment(assignmentId!);
  // TODO: This is ugly, try getting course_id from somewhere else, maybe from parents
  const { data: course } = useCourse(assignment?.course_id!);

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (isError || !assignment || !course ) {
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
            <p className={"text-sm text-muted-foreground whitespace-pre-line"}>{assignment.description}</p>

            <ScrollArea className={"w-full h-auto"}>
              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>Properties</h2>
                <Button variant={"secondary"} size={"sm"}>
                  <CircleCheck/> Completed
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Hourglass/> {assignment.deadline ? new Date(assignment.deadline).toLocaleDateString(undefined, { day: '2-digit', month: 'short' }) : 'No deadline'}
                </Button>
                <Button variant={"ghost"} size={"sm"}>
                  <Plus/>
                </Button>
              </div>

              <div className={"flex flex-row gap-1 mt-4 items-center"}>
                <h2 className={"text-muted-foreground mr-4 text-sm"}>Resources</h2>
                {/* <Button variant={"secondary"} size={"sm"}>
                  <LinkIcon/> 💻 BUCLES FOR ¿Qué son y...
                </Button>
                <Button variant={"secondary"} size={"sm"}>
                  <FileText/> ejercicios.docx
                </Button> */}
                <Button variant={"ghost"} size={"sm"}>
                  <Plus/>
                </Button>
              </div>

              <ScrollBar orientation="horizontal"/>
            </ScrollArea>

          </div>

          <div className={"space-y-5 mb-5"}>
            <h2 className={"text-xl font-semibold mb-3"}>Submissions</h2>
            <SubmissionsTable columns={columns} data={[]}/>
          </div>

        </div>
      </div>
      <WorkflowsSidebar side={"right"} className={"pt-16"}/>
    </SidebarProvider>
  );
}
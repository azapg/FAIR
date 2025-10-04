import {useCourse} from "@/hooks/use-courses";
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs"
import {BreadcrumbNav, BreadcrumbSegment} from "@/components/breadcrumb-nav";
import {Separator} from "@/components/ui/separator";
import AssignmentsTab from "@/app/courses/tabs/assignments/assignments-tab";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import {useParams, useNavigate, useLocation} from "react-router-dom";
import {useEffect} from "react";

const allowedTabs = ["assignments", "participants", "runs", "artifacts", "workflows", "plugins"];

export default function CourseDetailPage() {
  const params = useParams<{ courseId: string, tab: string }>()
  const {courseId, tab} = params;
  const navigate = useNavigate();
  const location = useLocation();

  const basePath = location.pathname.split('/').slice(0, -1).join('/');

  const {isLoading, isError, data: course} = useCourse(courseId, Boolean(courseId), true);

  const effectiveTab = tab && allowedTabs.includes(tab) ? tab : "assignments";

  useEffect(() => {
    if (!courseId || isLoading || isError || !course) return;
    if (!tab || !allowedTabs.includes(tab)) {
      navigate(`assignments`);
    }
  }, [tab, courseId, navigate, basePath, isLoading, isError, course]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (isError || !course) {
    return <div>Error loading course.</div>;
  }

  const segments: BreadcrumbSegment[] = [
    {label: "Courses", slug: "courses"},
    ...(courseId ? [{label: course?.name ?? "Course", slug: courseId}] : []),
    ...(tab ? [{label: tab.charAt(0).toUpperCase() + tab.slice(1), slug: tab}] : []),
  ];

  // Map assignments from detailed course if present
  const courseAssignments = 'assignments' in course ? course.assignments : [];

  return (
    <div className="flex flex-col">
      <div className={"py-2 px-5"}>
        <BreadcrumbNav segments={segments}/>
      </div>
      <Separator/>
      <div className={"px-8 py-5"}>
        <h1 className={"text-3xl font-bold pb-1"}>{course?.name}</h1>
        <p className={"text-sm text-muted-foreground"}>{course?.description}</p>
      </div>
      <Tabs value={effectiveTab} onValueChange={(val: string) => {
        if (!courseId) return;
        navigate(`${basePath}/${val}`, {replace: true});
      }}>
        <ScrollArea className={"w-full border-b"}>
          <TabsList className={"px-8 w-full"}>
            <TabsTrigger value="assignments">Assignments</TabsTrigger>
            <TabsTrigger value="participants">Participants</TabsTrigger>
            <TabsTrigger value="runs">Runs</TabsTrigger>
            <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
            <TabsTrigger value="workflows">Workflows</TabsTrigger>
            <TabsTrigger value="plugins">Plugins</TabsTrigger>
          </TabsList>
          <ScrollBar orientation="horizontal" className={"hidden"}/>
        </ScrollArea>
        <TabsContent value={"assignments"} className={"px-8 py-3"}>
          <AssignmentsTab assignments={courseAssignments} courseId={courseId}/>
        </TabsContent>
        <TabsContent value={"participants"} className={"px-8"}>participants</TabsContent>
        <TabsContent value={"runs"} className={"px-8"}>runs</TabsContent>
        <TabsContent value={"artifacts"} className={"px-8"}>artifacts</TabsContent>
        <TabsContent value={"workflows"} className={"px-8"}>workflows</TabsContent>
        <TabsContent value={"plugins"} className={"px-8"}>plugins</TabsContent>
      </Tabs>
    </div>
  );
}
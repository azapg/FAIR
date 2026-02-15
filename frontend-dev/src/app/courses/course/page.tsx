import {useCourse} from "@/hooks/use-courses";
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs"
import {BreadcrumbNav, BreadcrumbSegment} from "@/components/breadcrumb-nav";
import AssignmentsTab from "@/app/courses/tabs/assignments/assignments-tab";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import {useParams, useNavigate, useLocation} from "react-router-dom";
import {useEffect} from "react";
import {useTranslation} from "react-i18next";
import {useAssignments} from "@/hooks/use-assignments";
import {ParticipantsTab} from "@/app/courses/tabs/participants-tab";
import {RunsTab} from "@/app/courses/tabs/runs-tab";
import {ArtifactsTab} from "@/app/courses/tabs/artifacts-tab";
import {WorkflowsTab} from "@/app/courses/tabs/workflows-tab";
import {PluginsTab} from "@/app/courses/tabs/plugins-tab";
import {useWorkflowStore} from "@/store/workflows-store";
import {Badge} from "@/components/ui/badge";
import {Button} from "@/components/ui/button";
import {Switch} from "@/components/ui/switch";
import {Label} from "@/components/ui/label";
import {RefreshCw} from "lucide-react";
import {useResetEnrollmentCode, useUpdateCourseSettings} from "@/hooks/use-courses";
import {AuthUserRole, useAuth} from "@/contexts/auth-context";

const allowedTabs = ["assignments", "participants", "runs", "artifacts", "workflows", "plugins"];

export default function CourseDetailPage() {
  const params = useParams<{ courseId: string, tab: string }>()
  const {courseId, tab} = params;
  const navigate = useNavigate();
  const location = useLocation();
  const {t} = useTranslation();
  const {user} = useAuth();
  const {setActiveCourseId} = useWorkflowStore();
  const resetEnrollmentCode = useResetEnrollmentCode();
  const updateCourseSettings = useUpdateCourseSettings();

  const basePath = location.pathname.split('/').slice(0, -1).join('/');

  const {isLoading, isError, data: course} = useCourse(courseId, Boolean(courseId), true);
  const {data: assignmentsList} = useAssignments(courseId ? {course_id: courseId} : undefined, Boolean(courseId));

  const effectiveTab = tab && allowedTabs.includes(tab) ? tab : "assignments";

  useEffect(() => {
    if (!courseId || isLoading || isError || !course) return;
    if (!tab || !allowedTabs.includes(tab)) {
      navigate(`assignments`);
    }
  }, [tab, courseId, navigate, basePath, isLoading, isError, course]);

  useEffect(() => {
    if (courseId) {
      setActiveCourseId(courseId);
    }
  }, [courseId, setActiveCourseId]);

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError || !course) {
    return <div>{t("courses.errorLoading")}</div>;
  }

  const instructorId = "instructorId" in course ? course.instructorId : course.instructor?.id;
  const showEnrollmentControls =
    !!user &&
    (user.role === AuthUserRole.ADMIN ||
      (user.role === AuthUserRole.PROFESSOR && instructorId === user.id));
  const enrollmentCode =
    "enrollmentCode" in course ? course.enrollmentCode : undefined;
  const isEnrollmentEnabled =
    "isEnrollmentEnabled" in course ? course.isEnrollmentEnabled : false;

  const handleToggle = async (next: boolean) => {
    if (!courseId || !showEnrollmentControls) return;
    await updateCourseSettings.mutateAsync({
      id: courseId,
      data: { isEnrollmentEnabled: next },
    });
  };

  const handleResetCode = async () => {
    if (!courseId || !showEnrollmentControls) return;
    await resetEnrollmentCode.mutateAsync(courseId);
  };

  const segments: BreadcrumbSegment[] = [
    {label: t("courses.title"), slug: "courses"},
    ...(courseId ? [{label: course?.name ?? "Course", slug: courseId}] : []),
    ...(tab ? [{label: t(`tabs.${tab}`), slug: tab}] : []),
  ];

  // Map assignments from detailed course if present
  const courseAssignments = 'assignments' in course ? course.assignments : [];
  const assignments = assignmentsList ?? courseAssignments ?? [];

  return (
    <div className="flex flex-col">
      <div className={"py-2 px-5"}>
        <BreadcrumbNav segments={segments}/>
      </div>
      <div className={"px-8 py-2"}>
        <h1 className={"text-3xl font-bold pb-1"}>{course?.name}</h1>
        <p className={"text-sm text-muted-foreground"}>{course?.description}</p>
      </div>
      {showEnrollmentControls && (
        <div className="px-8 pb-3">
          <div className="flex flex-col gap-3 rounded-lg border bg-muted/40 px-4 py-3 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant={isEnrollmentEnabled ? "default" : "outline"}>
                  {t("courses.selfEnrollment")}
                </Badge>
                {!isEnrollmentEnabled && (
                  <span className="text-xs text-muted-foreground">
                    {t("courses.selfEnrollmentDisabled")}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono rounded-md border bg-background px-2 py-1 text-sm">
                  {enrollmentCode ?? "—"}
                </span>
                <span className="text-sm text-muted-foreground">
                  {t("courses.classCode")}
                </span>
              </div>
              <p className="text-sm text-muted-foreground max-w-xl">
                {t("courses.selfEnrollmentHint")}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Switch
                  checked={isEnrollmentEnabled}
                  onCheckedChange={handleToggle}
                  disabled={updateCourseSettings.isPending}
                />
                <Label className="text-sm">{t("courses.selfEnrollment")}</Label>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={handleResetCode}
                disabled={resetEnrollmentCode.isPending}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                {resetEnrollmentCode.isPending ? t("common.wait") : t("courses.resetCode")}
              </Button>
            </div>
          </div>
        </div>
      )}
      <Tabs value={effectiveTab} onValueChange={(val: string) => {
        if (!courseId) return;
        navigate(`${basePath}/${val}`, {replace: true});
      }}>
        <ScrollArea className={"w-full border-b"}>
          <TabsList className={"px-8 w-full"}>
            <TabsTrigger value="assignments">{t("tabs.assignments")}</TabsTrigger>
            <TabsTrigger value="participants">{t("tabs.participants")}</TabsTrigger>
            <TabsTrigger value="runs">{t("tabs.runs")}</TabsTrigger>
            <TabsTrigger value="artifacts">{t("tabs.artifacts")}</TabsTrigger>
            <TabsTrigger value="workflows">{t("tabs.workflows")}</TabsTrigger>
            <TabsTrigger value="plugins">{t("tabs.plugins")}</TabsTrigger>
          </TabsList>
          <ScrollBar orientation="horizontal" className={"hidden"}/>
        </ScrollArea>
        <TabsContent value={"assignments"} className={"px-8 py-3"}>
          <AssignmentsTab assignments={assignments} courseId={courseId}/>
        </TabsContent>
        <TabsContent value={"participants"} className={"px-8"}>
          <ParticipantsTab instructor={"instructor" in course ? course.instructor : undefined}/>
        </TabsContent>
        <TabsContent value={"runs"} className={"px-8"}>
          <RunsTab courseId={courseId}/>
        </TabsContent>
        <TabsContent value={"artifacts"} className={"px-8"}>
          <ArtifactsTab courseId={courseId} assignments={assignments}/>
        </TabsContent>
        <TabsContent value={"workflows"} className={"px-8"}>
          <WorkflowsTab courseId={courseId}/>
        </TabsContent>
        <TabsContent value={"plugins"} className={"px-8"}>
          <PluginsTab/>
        </TabsContent>
      </Tabs>
    </div>
  );
}

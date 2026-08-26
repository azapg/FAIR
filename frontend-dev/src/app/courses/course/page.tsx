import {hasStaffCourseMembership, useCourse, useCourses} from "@/hooks/use-courses";
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs"
import { PageHeader } from "@/components/page-header";
import AssignmentsTab from "@/app/courses/tabs/assignments/assignments-tab";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import {useParams, useNavigate, useLocation} from "react-router-dom";
import {useEffect} from "react";
import {useTranslation} from "react-i18next";
import {useAssignments} from "@/hooks/use-assignments";
import {ParticipantsTab} from "@/app/courses/tabs/participants-tab";
import {RunsTab} from "@/app/courses/tabs/runs-tab";
import {ArtifactsTab} from "@/app/courses/tabs/artifacts-tab";
import {FlowsTab} from "@/app/courses/tabs/flows-tab";
import {CapabilitiesTab} from "@/app/courses/tabs/capabilities-tab";
import { EnrollmentControls } from "../components/enrollment-controls";
import {useResetEnrollmentCode, useUpdateCourseSettings} from "@/hooks/use-courses";
import {useAuth} from "@/contexts/auth-context";
import {usePermission} from "@/hooks/use-permission";
import {GradebookTab} from "@/app/courses/tabs/gradebook-tab";
import {StreamTab} from "@/app/courses/tabs/stream-tab";
import {CourseContentTab} from "@/app/courses/tabs/content/course-content-tab";
import {StudentGradesTab} from "@/app/courses/tabs/student-grades-tab";
import {AuthUserRole} from "@/contexts/auth-context";
import { CourseCopyDialog } from "@/app/courses/components/course-copy-dialog";
type CourseTab = "stream" | "content" | "assignments" | "grades" | "gradebook" | "participants" | "runs" | "artifacts" | "flows" | "capabilities";

export default function CourseDetailPage() {
  const params = useParams<{ courseId: string, tab: string }>()
  const {courseId, tab} = params;
  const navigate = useNavigate();
  const location = useLocation();
  const {t} = useTranslation();
  const {user} = useAuth();
  const canManageAnyCourseSettings = usePermission("manage_course_settings_any");
  const canManageUsers = usePermission("manage_users");
  const resetEnrollmentCode = useResetEnrollmentCode();
  const updateCourseSettings = useUpdateCourseSettings();

  const basePath = location.pathname.split('/').slice(0, -1).join('/');

  const {isLoading, isError, data: course} = useCourse(courseId, Boolean(courseId), true);
  const {data: allCourses = []} = useCourses({include_archived: true}, Boolean(user));
  const {data: assignmentsList} = useAssignments(courseId ? {course_id: courseId} : undefined, Boolean(courseId));

  const hasActiveStaffCourse = hasStaffCourseMembership(allCourses);

  useEffect(() => {
    if (!courseId || isLoading || isError || !course) return;
    const instructorId = "instructorId" in course ? course.instructorId : course.instructor?.id;
    const isInstructorView = !!user && (
      instructorId === user.id || canManageUsers || course.membershipRole === 'assistant'
    );
    const isLearnerView = !isInstructorView && user?.role === AuthUserRole.USER && !hasActiveStaffCourse;
    const visibleTabs: CourseTab[] = isInstructorView
      ? ["stream", "content", "assignments", "gradebook", "participants", "runs", "artifacts", "flows", "capabilities"]
      : ["stream", "content", "assignments", ...(isLearnerView ? ["grades" as CourseTab] : []), "artifacts"];
    if (!tab || !visibleTabs.includes(tab as CourseTab)) {
      navigate(`assignments`);
    }
  }, [tab, courseId, navigate, basePath, isLoading, isError, course, user, canManageUsers, hasActiveStaffCourse]);

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError || !course) {
    return <div>{t("courses.errorLoading")}</div>;
  }

  const instructorId = "instructorId" in course ? course.instructorId : course.instructor?.id;
  const isCourseOwner = !!user && instructorId === user.id;
  const isCourseAdmin = !!user && canManageUsers;
  const isCourseAssistant = course.membershipRole === 'assistant';
  const isInstructorView = isCourseOwner || isCourseAdmin || isCourseAssistant;
  const isLearnerView = !isInstructorView && user?.role === AuthUserRole.USER && !hasActiveStaffCourse;
  const visibleTabs: CourseTab[] = isInstructorView
    ? ["stream", "content", "assignments", "gradebook", "participants", "runs", "artifacts", "flows", "capabilities"]
    : ["stream", "content", "assignments", ...(isLearnerView ? ["grades" as CourseTab] : []), "artifacts"];
  const currentTab = (tab && visibleTabs.includes(tab as CourseTab) ? tab : "assignments") as CourseTab;

  const showEnrollmentControls =
    !!user &&
    (canManageAnyCourseSettings || isCourseOwner);
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

  // Map assignments from detailed course if present
  const courseAssignments = 'assignments' in course ? course.assignments : [];
  const assignments = assignmentsList ?? courseAssignments ?? [];

  return (
    <div className="flex flex-col">
      <PageHeader
        title={course.name}
        description={course.description}
        actions={
          isInstructorView && courseId ? (
            <CourseCopyDialog courseId={courseId} name={course.name} />
          ) : undefined
        }
      />
      {showEnrollmentControls && (
        <EnrollmentControls
          enrollmentCode={enrollmentCode}
          isEnrollmentEnabled={isEnrollmentEnabled ?? false}
          onToggle={handleToggle}
          onResetCode={handleResetCode}
          isTogglePending={updateCourseSettings.isPending}
          isResetPending={resetEnrollmentCode.isPending}
          t={t}
        />
      )}
      <Tabs value={currentTab} onValueChange={(val: string) => {
        if (!courseId) return;
        navigate(`${basePath}/${val}`, {replace: true});
      }}>
        <ScrollArea className={"w-full border-b"}>
          <TabsList className={"px-6 sm:px-8 w-full"}>
            <TabsTrigger value="stream">Stream</TabsTrigger>
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="assignments">{t("tabs.assignments")}</TabsTrigger>
            {isInstructorView && <TabsTrigger value="gradebook">Gradebook</TabsTrigger>}
            {isLearnerView && <TabsTrigger value="grades">Grades</TabsTrigger>}
            <TabsTrigger value="artifacts">{t("tabs.artifacts")}</TabsTrigger>
            {isInstructorView && <TabsTrigger value="participants">{t("tabs.participants")}</TabsTrigger>}
            {isInstructorView && <TabsTrigger value="runs">{t("tabs.runs")}</TabsTrigger>}
            {isInstructorView && <TabsTrigger value="flows">Flows</TabsTrigger>}
            {isInstructorView && <TabsTrigger value="capabilities">Capabilities</TabsTrigger>}
          </TabsList>
          <ScrollBar orientation="horizontal" className={"hidden"}/>
        </ScrollArea>
        <TabsContent value={"assignments"} className={"px-6 sm:px-8 py-3"}>
          <AssignmentsTab assignments={assignments} courseId={courseId} canManageAssignments={isInstructorView}/>
        </TabsContent>
        <TabsContent value={"artifacts"} className={"px-6 sm:px-8"}>
          <ArtifactsTab courseId={courseId} assignments={assignments}/>
        </TabsContent>
        <TabsContent value={"stream"} className={"px-6 sm:px-8"}>
          <StreamTab courseId={courseId as string} canPost={isInstructorView}/>
        </TabsContent>
        <TabsContent value={"content"} className={"px-6 sm:px-8"}>
          <CourseContentTab
            courseId={courseId as string}
            canManage={isInstructorView}
            isArchived={course.isArchived}
            assignments={assignments}
          />
        </TabsContent>
        {isInstructorView && (
          <TabsContent value={"gradebook"} className={"px-6 sm:px-8"}>
            <GradebookTab courseId={courseId as string} isArchived={course.isArchived}/>
          </TabsContent>
        )}
        {isLearnerView && (
          <TabsContent value={"grades"} className={"px-4 sm:px-6 sm:px-8"}>
            <StudentGradesTab courseId={courseId as string} enabled={currentTab === 'grades'}/>
          </TabsContent>
        )}
        {isInstructorView && (
          <TabsContent value={"participants"} className={"px-6 sm:px-8"}>
            <ParticipantsTab
              courseId={courseId as string}
              instructor={"instructor" in course ? course.instructor : undefined}
              canManageRoles={isCourseOwner || isCourseAdmin}
            />
          </TabsContent>
        )}
        {isInstructorView && (
          <TabsContent value={"runs"} className={"px-6 sm:px-8"}>
            <RunsTab courseId={courseId}/>
          </TabsContent>
        )}
        {isInstructorView && (
          <TabsContent value={"flows"} className={"px-6 sm:px-8"}>
            <FlowsTab courseId={courseId}/>
          </TabsContent>
        )}
        {isInstructorView && (
          <TabsContent value={"capabilities"} className={"px-6 sm:px-8"}>
            <CapabilitiesTab/>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

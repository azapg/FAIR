import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  BookOpen,
  ClipboardList,
  GraduationCap,
  MessageSquare,
  Settings,
  Users,
} from "lucide-react";
import {
  hasStaffCourseMembership,
  useCourse,
  useCourses,
  useResetEnrollmentCode,
  useUpdateCourseSettings,
} from "@/hooks/use-courses";
import { useAuth, AuthUserRole } from "@/contexts/auth-context";
import { usePermission } from "@/hooks/use-permission";
import { useAssignments } from "@/hooks/use-assignments";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FloatingNav, type FloatingNavItem } from "@/components/floating-nav";
import { EnrollmentControls } from "../components/enrollment-controls";
import { CourseStreamSidebar } from "../components/course-stream-sidebar";
import {
  CourseSettingsDialog,
  type CourseSettingsSection,
} from "../components/course-settings-dialog";
import { CourseIcon } from "../course-icons";
import AssignmentsTab from "../tabs/assignments/assignments-tab";
import { CreateAssignmentDialog } from "../tabs/assignments/create-assignment-dialog";
import { StreamTab } from "../tabs/stream-tab";
import { CourseContentTab } from "../tabs/content/course-content-tab";
import { GradebookTab } from "../tabs/gradebook-tab";
import { StudentGradesTab } from "../tabs/student-grades-tab";
import { ParticipantsTab } from "../tabs/participants-tab";
import { ArtifactsTab } from "../tabs/artifacts-tab";

import { useReleaseFeatures } from "@/hooks/use-release-features";

const ADVANCED_TABS = ["runs", "flows", "capabilities", "artifacts"] as const;

export default function CourseDetailPage() {
  const { courseId, tab } = useParams<{ courseId: string; tab: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuth();
  const flags = useReleaseFeatures();
  const canManageAnyCourseSettings = usePermission(
    "manage_course_settings_any",
  );
  const canManageUsers = usePermission("manage_users");
  const resetEnrollmentCode = useResetEnrollmentCode();
  const updateCourseSettings = useUpdateCourseSettings();
  const [isCreateAssignmentOpen, setIsCreateAssignmentOpen] = useState(false);
  const [isComposerOpen, setIsComposerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const courseQuery = useCourse(courseId, Boolean(courseId), true);
  const { data: course, isLoading, isError } = courseQuery;
  const { data: allCourses = [] } = useCourses(
    { include_archived: true },
    Boolean(user),
  );
  const assignmentQuery = useAssignments(
    courseId ? { course_id: courseId } : undefined,
    Boolean(courseId),
  );
  const instructorId =
    course &&
    ("instructorId" in course ? course.instructorId : course.instructor?.id);
  const isCourseOwner = !!user && instructorId === user.id;
  const isCourseAdmin = !!user && canManageUsers;
  const isInstructorView =
    isCourseOwner || isCourseAdmin || course?.membershipRole === "assistant";
  const isLearnerView =
    !isInstructorView &&
    user?.role === AuthUserRole.USER &&
    !hasStaffCourseMembership(allCourses);
  const showEnrollmentControls =
    !!user &&
    (canManageAnyCourseSettings || isCourseOwner) &&
    !course?.isArchived;
  const advancedSection =
    isInstructorView &&
    (flags.extensions || tab === "artifacts") &&
    ADVANCED_TABS.includes(tab as (typeof ADVANCED_TABS)[number])
      ? (tab as CourseSettingsSection)
      : undefined;
  const primaryTabs = [
    "stream",
    ...(flags.course_content ? ["content"] : []),
    "assignments",
    ...(isInstructorView
      ? [...(flags.gradebook ? ["gradebook"] : []), "participants"]
      : []),
    ...(isLearnerView && flags.gradebook ? ["grades"] : []),
    ...(!isInstructorView ? ["artifacts"] : []),
  ];
  const validTab = primaryTabs.includes(tab ?? "") || !!advancedSection;
  const currentTab = advancedSection ? "stream" : validTab ? tab! : "stream";
  const basePath = `/courses/${courseId}`;

  useEffect(() => {
    if (!course || isLoading || isError || !courseId || flags.isPending) return;
    if (!validTab || tab === "timeline")
      navigate(`/courses/${courseId}/stream`, { replace: true });
  }, [
    course,
    isLoading,
    isError,
    courseId,
    tab,
    validTab,
    navigate,
    flags.isPending,
  ]);

  if (isLoading)
    return (
      <div className="p-8 text-muted-foreground">{t("common.loading")}</div>
    );
  if (isError || !course || !courseId)
    return <div className="p-8">{t("courses.errorLoading")}</div>;

  const assignments =
    assignmentQuery.data ?? ("assignments" in course ? course.assignments : []);
  const enrollmentControls = showEnrollmentControls ? (
    <EnrollmentControls
      enrollmentCode={course.enrollmentCode}
      isEnrollmentEnabled={course.isEnrollmentEnabled ?? false}
      onToggle={(next) =>
        updateCourseSettings
          .mutateAsync({ id: courseId, data: { isEnrollmentEnabled: next } })
          .then(() => {})
      }
      onResetCode={() =>
        resetEnrollmentCode.mutateAsync(courseId).then(() => {})
      }
      isTogglePending={updateCourseSettings.isPending}
      isResetPending={resetEnrollmentCode.isPending}
    />
  ) : undefined;
  const goToTab = (value: string) =>
    navigate(`${basePath}/${value}`, { replace: true });
  const closeSettings = () => {
    setSettingsOpen(false);
    if (advancedSection) goToTab("stream");
  };
  const canPost = isInstructorView && !course.isArchived;
  const navItems: FloatingNavItem[] = [
    { value: "stream", label: "Stream", icon: MessageSquare },
    ...(flags.course_content
      ? [{ value: "content", label: "Content", icon: BookOpen }]
      : []),
    { value: "assignments", label: t("tabs.assignments"), icon: ClipboardList },
    ...(isInstructorView
      ? [
          ...(flags.gradebook
            ? [{ value: "gradebook", label: "Gradebook", icon: GraduationCap }]
            : []),
          { value: "participants", label: t("tabs.participants"), icon: Users },
        ]
      : []),
    ...(isLearnerView && flags.gradebook
      ? [{ value: "grades", label: "Grades", icon: GraduationCap }]
      : []),
    ...(!isInstructorView
      ? [{ value: "artifacts", label: "Files", icon: BookOpen }]
      : []),
  ];

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col pb-24 md:pb-8">
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-[10px] bg-primary/10 text-primary">
              <CourseIcon iconKey={course.iconKey} size={24} />
            </span>
            <span>{course.name}</span>
          </span>
        }
        description={course.description}
        actions={
          isInstructorView ? (
            <Button
              variant="ghost"
              size="icon"
              aria-label="Course settings"
              title="Course settings"
              onClick={() => setSettingsOpen(true)}
            >
              <Settings />
            </Button>
          ) : undefined
        }
      />
      <div className="mx-auto mt-6 w-full max-w-[1440px] px-6 sm:px-8">
        {course.isArchived && (
          <p className="mb-4 text-sm text-muted-foreground">Archived course</p>
        )}
        <Tabs value={currentTab} onValueChange={goToTab} className="gap-6">
          <div className="hidden overflow-x-auto md:block">
            <TabsList
              className="h-auto gap-1 border-0"
              aria-label="Course navigation"
            >
              {navItems.map((item) => (
                <TabsTrigger
                  key={item.value}
                  value={item.value}
                  className="m-0 rounded-md border-0 px-3 py-2 data-[state=active]:bg-muted"
                >
                  {item.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
          <TabsContent value="stream">
            <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_13rem] md:gap-8 xl:grid-cols-[minmax(0,1fr)_15rem] xl:gap-10">
              <div className="order-2 min-w-0 md:order-1">
                <StreamTab
                  courseId={courseId}
                  canPost={canPost}
                  assignments={assignments}
                  assignmentsLoading={assignmentQuery.isPending}
                  assignmentsError={assignmentQuery.isError}
                  onRetryAssignments={() => {
                    void assignmentQuery.refetch();
                  }}
                  onCreateAssignment={() => setIsCreateAssignmentOpen(true)}
                  composerOpen={isComposerOpen}
                  onComposerOpenChange={setIsComposerOpen}
                />
              </div>
              <div className="order-1 min-w-0 md:order-2">
                <CourseStreamSidebar
                  courseId={courseId}
                  assignments={assignments}
                  canReview={isInstructorView && flags.gradebook}
                  enrollmentControls={enrollmentControls}
                />
              </div>
            </div>
          </TabsContent>
          <TabsContent value="assignments">
            <AssignmentsTab
              assignments={assignments}
              courseId={courseId}
              canManageAssignments={canPost}
              onCreateAssignment={
                canPost ? () => setIsCreateAssignmentOpen(true) : undefined
              }
            />
          </TabsContent>
          {flags.course_content && (
            <TabsContent value="content">
              <CourseContentTab
                courseId={courseId}
                canManage={isInstructorView}
                isArchived={course.isArchived}
                assignments={assignments}
              />
            </TabsContent>
          )}
          {isInstructorView && flags.gradebook && (
            <TabsContent value="gradebook">
              <GradebookTab
                courseId={courseId}
                isArchived={course.isArchived}
              />
            </TabsContent>
          )}
          {isInstructorView && (
            <TabsContent value="participants">
              <ParticipantsTab
                courseId={courseId}
                instructor={
                  "instructor" in course ? course.instructor : undefined
                }
                canManageRoles={isCourseOwner || isCourseAdmin}
              />
            </TabsContent>
          )}
          {isLearnerView && flags.gradebook && (
            <TabsContent value="grades">
              <StudentGradesTab
                courseId={courseId}
                enabled={currentTab === "grades"}
              />
            </TabsContent>
          )}
          {!isInstructorView && (
            <TabsContent value="artifacts">
              <ArtifactsTab courseId={courseId} assignments={assignments} />
            </TabsContent>
          )}
        </Tabs>
      </div>
      <FloatingNav
        value={currentTab}
        onValueChange={goToTab}
        items={navItems}
      />
      {canPost && (
        <CreateAssignmentDialog
          courseId={courseId}
          onAssignmentCreated={() => {}}
          open={isCreateAssignmentOpen}
          onOpenChange={setIsCreateAssignmentOpen}
          showTrigger={false}
        />
      )}
      {isInstructorView && (settingsOpen || advancedSection) && (
        <CourseSettingsDialog
          key={courseId}
          course={course}
          assignments={assignments}
          canEdit={isCourseOwner || isCourseAdmin}
          enrollmentControls={enrollmentControls}
          initialSection={advancedSection}
          onClose={closeSettings}
        />
      )}
    </div>
  );
}

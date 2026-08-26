import {Button} from "@/components/ui/button";
import {LogIn, Plus} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {FormEvent, useState} from "react";
import {useCourses, useCreateCourse, useDeleteCourse, Course, useJoinCourseByCode} from "@/hooks/use-courses";
import {useAuth} from "@/contexts/auth-context";
import CourseGrid from "@/app/courses/components/course-grid";
import CourseFormDialog from "@/app/courses/components/course-form-dialog";
import { PageHeader } from "@/components/page-header";
import { FloatingNav, FloatingActionButton } from "@/components/floating-nav";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {useTranslation} from "react-i18next";
import {Dialog, DialogFooter, DialogHeader, DialogTitle} from "@/components/ui/dialog";
import {ResponsiveDialogContent} from "@/components/ui/responsive-dialog";
import {Label} from "@/components/ui/label";
import {Input} from "@/components/ui/input";
import {usePermission} from "@/hooks/use-permission";

export default function CoursesPage() {
  const navigate = useNavigate();
  const {user, isAuthenticated} = useAuth();
  const {data, isPending, isError} = useCourses();
  const createCourse = useCreateCourse();
  const deleteCourse = useDeleteCourse();
  const joinCourse = useJoinCourseByCode();
  const {t} = useTranslation();

  const [open, setOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const courses: Course[] = data ?? [];
  const hasCreateCoursePermission = usePermission("create_course");
  const hasJoinCoursePermission = usePermission("join_course");
  const canCreateCourses = isAuthenticated && hasCreateCoursePermission;
  const canJoinCourses = isAuthenticated && hasJoinCoursePermission;

  const openCreateDialog = () => {
    setName("");
    setDescription("");
    setOpen(true);
  };

  const openJoinDialog = () => {
    setJoinCode("");
    setJoinOpen(true);
  };

  const onSubmitCreateAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated || !user) return;
    if (!name.trim()) return;

    // TODO: handle error
    await createCourse.mutateAsync({
      name: name.trim(),
      description: description.trim() || null,
      instructorId: user.id,
    });

    setName("");
    setDescription("");
    setOpen(false);
  };

  const onSubmitJoinAction = async (e: FormEvent) => {
    e.preventDefault();
    if (!canJoinCourses) return;
    const trimmed = joinCode.trim();
    if (!trimmed) return;

    await joinCourse.mutateAsync(trimmed);
    setJoinCode("");
    setJoinOpen(false);
  };

  const handleDeleteCourse = async (course: Course) => {
    await deleteCourse.mutateAsync(course.id);
  };

  const handleCourseClick = (courseId: string) => {
    navigate(`${courseId}`);
  };

  return (
    <main className="flex flex-col justify-center pb-24 md:pb-0">
      <PageHeader
        title={t("courses.yourCourses")}
        actions={
          <div className="hidden gap-2 md:flex">
            {canJoinCourses && (
              <Button variant="outline" onClick={openJoinDialog}>
                {t("courses.joinCourse")}
              </Button>
            )}

            {canCreateCourses && (
              <CourseFormDialog
                open={open}
                onOpenChangeAction={setOpen}
                mode="create"
                name={name}
                description={description}
                onNameChangeAction={setName}
                onDescriptionChangeAction={setDescription}
                onSubmitAction={onSubmitCreateAction}
                isSubmitting={createCourse.isPending}
                isDisabled={createCourse.isPending || !isAuthenticated}
                trigger={
                  <Button onClick={openCreateDialog}>
                    <Plus className="mr-2"/>
                    {t("common.create")}
                  </Button>
                }
              />
            )}
          </div>
        }
      />

      <div className={"px-6"}>
        <CourseGrid
          courses={courses}
          isPending={isPending}
          isError={isError}
          onCardClickAction={handleCourseClick}
          onDeleteAction={handleDeleteCourse}
          onCreateCourse={canCreateCourses ? openCreateDialog : undefined}
          emptyActionSlot={canJoinCourses ? (
            <Button onClick={openJoinDialog}>
              {t("courses.joinCourseCta")}
            </Button>
          ) : undefined}
        />
      </div>

      <FloatingNav
        items={[]}
        value=""
        onValueChange={() => {}}
        action={
          (canCreateCourses || canJoinCourses) && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <FloatingActionButton aria-label={t("common.add")}>
                  <Plus className="size-5" />
                </FloatingActionButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="end" className="mb-2">
                {canJoinCourses && (
                  <DropdownMenuItem onClick={() => setJoinOpen(true)}>
                    <LogIn />
                    {t("courses.joinCourse")}
                  </DropdownMenuItem>
                )}
                {canCreateCourses && (
                  <DropdownMenuItem onClick={() => openCreateDialog()}>
                    <Plus />
                    {t("courses.createCourse")}
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )
        }
      />

      <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
        <ResponsiveDialogContent>
          <DialogHeader>
            <DialogTitle>{t("courses.joinCourse")}</DialogTitle>
          </DialogHeader>
          <form onSubmit={onSubmitJoinAction} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="join-code">{t("courses.enterCode")}</Label>
              <Input
                id="join-code"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value)}
                placeholder={t("courses.codePlaceholder")}
                autoFocus
                required
                disabled={joinCourse.isPending}
              />
            </div>
            <DialogFooter>
              <Button variant="ghost" type="button" onClick={() => setJoinOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={joinCourse.isPending || !joinCode.trim()}>
                {joinCourse.isPending ? t("common.wait") : t("courses.joinCourse")}
              </Button>
            </DialogFooter>
          </form>
        </ResponsiveDialogContent>
      </Dialog>
    </main>
  );
}

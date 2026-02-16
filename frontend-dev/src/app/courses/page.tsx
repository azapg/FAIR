import {Button} from "@/components/ui/button";
import {Plus} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {FormEvent, useState} from "react";
import {useCourses, useCreateCourse, useDeleteCourse, Course, useJoinCourseByCode} from "@/hooks/use-courses";
import {AuthUserRole, useAuth} from "@/contexts/auth-context";
import CourseGrid from "@/app/courses/components/course-grid";
import CourseFormDialog from "@/app/courses/components/course-form-dialog";
import {BreadcrumbNav} from "@/components/breadcrumb-nav";
import {useTranslation} from "react-i18next";
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle} from "@/components/ui/dialog";
import {Label} from "@/components/ui/label";
import {Input} from "@/components/ui/input";

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
  const isStudent = user?.role === AuthUserRole.STUDENT;
  const canCreateCourses = isAuthenticated && !isStudent;
  const canJoinCourses = isAuthenticated && isStudent;

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
    <main className="flex flex-col justify-center">
      <div className={"py-2 px-5"}>
        <BreadcrumbNav segments={[
          {
            label: t("courses.title"),
            slug: "courses"
          }
        ]}/>
      </div>
      <div className="flex items-center justify-between px-6 pt-3">
        <h1 className="text-3xl">{t("courses.yourCourses")}</h1>

        <div className="flex items-center gap-2">
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
      </div>

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

      <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
        <DialogContent>
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
        </DialogContent>
      </Dialog>
    </main>
  );
}

import {Button} from "@/components/ui/button";
import {Plus} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {useState} from "react";
import {useCourses, useCreateCourse, useDeleteCourse, Course} from "@/hooks/use-courses";
import {useAuth} from "@/contexts/auth-context";
import CourseGrid from "@/app/courses/components/course-grid";
import CourseFormDialog from "@/app/courses/components/course-form-dialog";
import {BreadcrumbNav} from "@/components/breadcrumb-nav";
import {Separator} from "@/components/ui/separator";
import {useTranslation} from "react-i18next";

export default function CoursesPage() {
  const navigate = useNavigate();
  const {user, isAuthenticated} = useAuth();
  const {data, isPending, isError} = useCourses();
  const createCourse = useCreateCourse();
  const deleteCourse = useDeleteCourse();
  const {t} = useTranslation();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const courses: Course[] = data ?? [];

  const openCreateDialog = () => {
    setName("");
    setDescription("");
    setOpen(true);
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
      <Separator/>
      <div className="flex items-center justify-between px-6 pt-5">
        <h1 className="text-3xl">{t("courses.yourCourses")}</h1>

        {isAuthenticated && (<CourseFormDialog
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
        />)}
      </div>

      <div className={"px-6"}>
        <CourseGrid
          courses={courses}
          isPending={isPending}
          isError={isError}
          onCardClickAction={handleCourseClick}
          onDeleteAction={handleDeleteCourse}
        />
      </div>
    </main>
  );
}

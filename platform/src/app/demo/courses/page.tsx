import {Button} from "@/components/ui/button";
import {Plus} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {useState} from "react";
import {useCourses, useCreateCourse, useDeleteCourse, Course, Id} from "@/hooks/use-courses";
import {useAuth} from "@/contexts/auth-context";
import CourseGrid from "@/app/demo/components/course-grid";
import CourseFormDialog from "@/app/demo/components/course-form-dialog";
import {BreadcrumbNav} from "@/app/demo/components/breadcrumb-nav";
import {Separator} from "@/components/ui/separator";

export default function CoursesPage() {
  const navigate = useNavigate();
  const {user, isAuthenticated} = useAuth();
  const {data, isPending, isError} = useCourses();
  const createCourse = useCreateCourse();
  const deleteCourse = useDeleteCourse();

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
      instructor_id: user.id,
    });

    setName("");
    setDescription("");
    setOpen(false);
  };

  const handleDeleteCourse = async (course: Course) => {
    await deleteCourse.mutateAsync(course.id);
  };

  const handleCourseClick = (courseId: Id) => {
    navigate(`${courseId}`);
  };

  return (
    <main className="flex flex-col justify-center">
      <div className={"py-2 px-5"}>
        <BreadcrumbNav baseUrl="demo" segments={[
          {
            label: "Courses",
            slug: "courses"
          }
        ]}/>
      </div>
      <Separator/>
      <div className="flex items-center justify-between px-6 pt-5">
        <h1 className="text-3xl">Your courses</h1>

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
              Create
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

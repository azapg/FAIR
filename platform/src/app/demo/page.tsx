"use client";

import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useCourses, useCreateCourse, useDeleteCourse, Course, Id } from "@/hooks/use-courses";
import { useAuth } from "@/contexts/auth-context";
import CourseGrid from "@/app/demo/components/course-grid";
import CourseFormDialog from "@/app/demo/components/course-form-dialog";

export default function CoursesPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const { data, isPending, isError } = useCourses();
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
  router.push(`/demo/courses/${courseId}`);
  };

  return (
    <main className="p-5 flex flex-col justify-center">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl">Your courses</h1>

        { isAuthenticated && (<CourseFormDialog
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
              <Plus className="mr-2" />
              Create
            </Button>
          }
        />)}
      </div>

      <CourseGrid
        courses={courses}
        isPending={isPending}
        isError={isError}
        onCardClickAction={handleCourseClick}
        onDeleteAction={handleDeleteCourse}
      />
    </main>
  );
}

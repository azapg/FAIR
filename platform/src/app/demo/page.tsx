"use client";

import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useCourses, useCreateCourse, useUpdateCourse, useDeleteCourse, Course, Id } from "@/hooks/use-courses";
import { useAuth } from "@/contexts/auth-context";
import CourseGrid from "@/app/demo/components/course-grid";
import CourseFormDialog, { type CourseFormMode } from "@/app/demo/components/course-form-dialog";

export default function CoursesPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const { data, isPending, isError } = useCourses();
  const createCourse = useCreateCourse();
  const updateCourse = useUpdateCourse();
  const deleteCourse = useDeleteCourse();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [dialogMode, setDialogMode] = useState<CourseFormMode>("create");
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);

  const courses: Course[] = data ?? [];

  const openCreateDialog = () => {
    setDialogMode("create");
    setEditingCourse(null);
    setName("");
    setDescription("");
    setOpen(true);
  };

  const openEditDialog = (course: Course) => {
    setDialogMode("edit");
    setEditingCourse(course);
    setName(course.name);
    setDescription(course.description ?? "");
    setOpen(true);
  };

  const openCloneDialog = (course: Course) => {
    setDialogMode("clone");
    setEditingCourse(course);
    setName(course.name + " (Copy)");
    setDescription(course.description ?? "");
    setOpen(true);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated || !user) return;
    if (!name.trim()) return;

    if (dialogMode === "create" || dialogMode === "clone") {
      await createCourse.mutateAsync({
        name: name.trim(),
        description: description.trim() || null,
        instructor_id: user.id,
      });
    } else if (dialogMode === "edit" && editingCourse) {
      await updateCourse.mutateAsync({
        id: editingCourse.id,
        data: {
          name: name.trim(),
          description: description.trim() || null,
        },
      });
    }

    setName("");
    setDescription("");
    setEditingCourse(null);
    setOpen(false);
  };

  const handleDeleteCourse = async (course: Course) => {
    if (window.confirm(`Delete course "${course.name}"? This cannot be undone.`)) {
      await deleteCourse.mutateAsync(course.id);
    }
  };

  const handleCourseClick = (courseId: Id) => {
    router.push(`/demo/assignment?courseId=${courseId}`);
  };

  return (
    <main className="p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl">Your courses</h1>

        <CourseFormDialog
          open={open}
          onOpenChangeAction={setOpen}
          mode={dialogMode}
          name={name}
          description={description}
          onNameChangeAction={setName}
          onDescriptionChangeAction={setDescription}
          onSubmitAction={onSubmit}
          isSubmitting={createCourse.isPending || updateCourse.isPending}
          isDisabled={createCourse.isPending || updateCourse.isPending || !isAuthenticated}
          trigger={
            <Button onClick={openCreateDialog}>
              <Plus className="mr-2" />
              Create
            </Button>
          }
        />
      </div>

      {isError && (
        <div className="text-sm text-red-600 mb-4 p-3 bg-red-50 rounded-md">Failed to load courses</div>
      )}

      <CourseGrid
        courses={courses}
        isPending={isPending}
        onCardClickAction={handleCourseClick}
        onEditAction={openEditDialog}
        onCloneAction={openCloneDialog}
        onDeleteAction={handleDeleteCourse}
      />
    </main>
  );
}

"use client";

import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Skeleton} from "@/components/ui/skeleton";
import {Plus} from "lucide-react";
import {useRouter} from "next/navigation";
import {useState} from "react";
import {useCourses, useCreateCourse, useUpdateCourse, useDeleteCourse, Course, Id} from "@/hooks/use-courses";
import {Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger} from "@/components/ui/dialog";
import {Label} from "@/components/ui/label";
import {Input} from "@/components/ui/input";
import {Textarea} from "@/components/ui/textarea";
import {useAuth} from "@/contexts/auth-context";
import {DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger} from "@/components/ui/dropdown-menu";
import {MoreVertical} from "lucide-react";

const CourseCardSkeleton = () => (
  <Card className="bg-gray-50 cursor-wait flex flex-col h-full">
    <CardHeader className="flex-1 flex flex-col items-start">
      <CardTitle>
        <Skeleton className="h-[20px] w-32 rounded-full bg-gray-200"/>
      </CardTitle>
      <CardDescription className="space-y-2 mt-2">
        <Skeleton className="h-4 w-40 bg-gray-200"/>
        <Skeleton className="h-4 w-28 bg-gray-200"/>
      </CardDescription>
    </CardHeader>
    <CardFooter>
      <Skeleton className="h-4 w-24 bg-gray-200"/>
    </CardFooter>
  </Card>
);

export default function CoursesPage() {
  const router = useRouter();
  const {user, isAuthenticated} = useAuth()
  const {data, isPending, isError} = useCourses()
  const createCourse = useCreateCourse()
  const updateCourse = useUpdateCourse()
  const deleteCourse = useDeleteCourse()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  const [dialogMode, setDialogMode] = useState<'create' | 'edit' | 'clone'>('create')
  const [editingCourse, setEditingCourse] = useState<Course | null>(null)

  const courses: Course[] = data ?? []

  const openCreateDialog = () => {
    setDialogMode('create')
    setEditingCourse(null)
    setName("")
    setDescription("")
    setOpen(true)
  }

  const openEditDialog = (course: Course) => {
    setDialogMode('edit')
    setEditingCourse(course)
    setName(course.name)
    setDescription(course.description ?? "")
    setOpen(true)
  }

  const openCloneDialog = (course: Course) => {
    setDialogMode('clone')
    setEditingCourse(course)
    setName(course.name + " (Copy)")
    setDescription(course.description ?? "")
    setOpen(true)
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isAuthenticated || !user) return
    if (!name.trim()) return

    if (dialogMode === 'create' || dialogMode === 'clone') {
      await createCourse.mutateAsync({
        name: name.trim(),
        description: description.trim() || null,
        instructor_id: user.id,
      })
    } else if (dialogMode === 'edit' && editingCourse) {
      await updateCourse.mutateAsync({
        id: editingCourse.id,
        data: {
          name: name.trim(),
          description: description.trim() || null,
        },
      })
    }

    setName("")
    setDescription("")
    setEditingCourse(null)
    setOpen(false)
  }

  const handleDeleteCourse = async (course: Course) => {
    if (window.confirm(`Delete course "${course.name}"? This cannot be undone.`)) {
      await deleteCourse.mutateAsync(course.id)
    }
  }

  const handleCourseClick = (courseId: Id) => {
    router.push(`/demo/assignment?courseId=${courseId}`);
  };

  return (
    <main className="p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl">Your courses</h1>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreateDialog}>
              <Plus className="mr-2"/>
              Create
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {dialogMode === 'edit' ? "Edit course" : dialogMode === 'clone' ? "Clone course" : "Create course"}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="course-name">Name</Label>
                <Input
                  id="course-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Intro to AI"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="course-description">Description</Label>
                <Textarea
                  id="course-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional short description"
                />
              </div>
              <DialogFooter>
                <Button
                  type="submit"
                  disabled={
                    createCourse.isPending ||
                    updateCourse.isPending ||
                    !isAuthenticated
                  }
                >
                  {(createCourse.isPending || updateCourse.isPending)
                    ? "Wait..."
                    : dialogMode === 'edit'
                      ? "Save"
                      : dialogMode === 'clone'
                        ? "Clone"
                        : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isError && (
        <div className="text-sm text-red-600 mb-4 p-3 bg-red-50 rounded-md">
          Failed to load courses
        </div>
      )}

      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-7 mt-6">
        {isPending
          ? Array.from({length: 6}, (_, i) => <CourseCardSkeleton key={i}/>)
          : courses.length === 0 ? (
            <div className="col-span-full flex flex-col items-center justify-center py-16 h-full">
                <span className="text-lg font-serif text-gray-500">
                  No courses yet. Create one to get started.
                </span>
            </div>
          ) : (
            courses.map((course) => (
              <Card key={course.id} className="flex flex-col bg-amber-50 hover:bg-amber-100 transition-colors relative"
                    onClick={() => handleCourseClick(course.id)}>
                <div className="absolute top-3 right-3 z-10">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" tabIndex={0} aria-label="Course actions"
                        onClick={e => {e.stopPropagation();}}>
                        <MoreVertical className="w-5 h-5"/>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" onClick={e => e.stopPropagation()}>
                      <DropdownMenuItem onClick={() => {openEditDialog(course)}}>
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => {openCloneDialog(course)}}>
                        Clone
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-red-600"
                        onClick={() => {handleDeleteCourse(course).then()}}>
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <CardHeader className="flex-1 flex flex-col items-start">
                  <CardTitle>{course.name}</CardTitle>
                  {course.description && (
                    <CardDescription>{course.description}</CardDescription>
                  )}
                </CardHeader>
                <CardFooter>
                  {/* TODO: fetch name and number of assignments? seems expensive... */}
                  Instructor: {String(course.instructor_id)}
                </CardFooter>
              </Card>
            ))
          )
        }
      </div>
    </main>
  );
}

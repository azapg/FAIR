"use client";

import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MoreVertical } from "lucide-react";
import type { Course, Id } from "@/hooks/use-courses";
import { useCreateCourse, useUpdateCourse } from "@/hooks/use-courses";
import { useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent as ConfirmContent,
  AlertDialogDescription,
  AlertDialogFooter as ConfirmFooter,
  AlertDialogHeader as ConfirmHeader,
  AlertDialogTitle as ConfirmTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export type CourseCardProps = {
  course: Course;
  onClickAction?: (id: Id) => void;
  onDeleteAction?: (course: Course) => void;
};

type Mode = "edit" | "clone";

export default function CourseCard({ course, onClickAction, onDeleteAction }: CourseCardProps) {
  const { user, isAuthenticated } = useAuth();
  const updateCourse = useUpdateCourse();
  const createCourse = useCreateCourse();

  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("edit");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [confirmName, setConfirmName] = useState("");
  const isConfirmCorrect = confirmName === course.name;

  const setupEdit = () => {
    setMode("edit");
    setName(course.name);
    setDescription(course.description ?? "");
  };

  const setupClone = () => {
    setMode("clone");
    setName(course.name + " (Copy)");
    setDescription(course.description ?? "");
  };

  const isSubmitting = updateCourse.isPending || createCourse.isPending;
  const isDisabled = isSubmitting || !isAuthenticated;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (mode === "edit") {
      await updateCourse.mutateAsync({
        id: course.id,
        data: { name: name.trim(), description: description.trim() || null },
      });
    } else if (mode === "clone") {
      if (!user) return;
      await createCourse.mutateAsync({
        name: name.trim(),
        description: description.trim() || null,
        instructor_id: user.id,
      });
    }
    setOpen(false);
  };

  return (
    <Card
      className="flex flex-col bg-amber-50 hover:bg-amber-100 transition-colors relative cursor-pointer"
      onClick={() => onClickAction?.(course.id)}
    >
      <div className="absolute top-3 right-3 z-10" onClick={(e) => e.stopPropagation()}>
        <Dialog open={open} onOpenChange={setOpen}>
          <AlertDialog onOpenChange={(isOpen) => { if (!isOpen) setConfirmName(""); }}>
            <DropdownMenu modal={false}>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" tabIndex={0} aria-label="Course actions">
                  <MoreVertical className="w-5 h-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DialogTrigger asChild>
                  <DropdownMenuItem onClick={setupEdit}>Edit</DropdownMenuItem>
                </DialogTrigger>
                <DialogTrigger asChild>
                  <DropdownMenuItem onClick={setupClone}>Clone</DropdownMenuItem>
                </DialogTrigger>
                <AlertDialogTrigger asChild>
                  <DropdownMenuItem className="text-red-600">Delete</DropdownMenuItem>
                </AlertDialogTrigger>
              </DropdownMenuContent>
            </DropdownMenu>

            <ConfirmContent onClick={(e) => e.stopPropagation()}>
              <ConfirmHeader>
                <ConfirmTitle>Delete course</ConfirmTitle>
                <AlertDialogDescription>
                  This action cannot be undone. To confirm deletion, type the course name exactly:
                  <span className="font-medium"> {course.name}</span>
                </AlertDialogDescription>
              </ConfirmHeader>
              <div className="space-y-2">
                <Label htmlFor={`confirm-name-${course.id}`}>Course name</Label>
                <Input
                  id={`confirm-name-${course.id}`}
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  placeholder={course.name}
                  autoFocus
                />
              </div>
              <ConfirmFooter>
                <AlertDialogCancel onClick={(e) => e.stopPropagation()}>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  disabled={!isConfirmCorrect}
                  onClick={(e) => {
                    if (!isConfirmCorrect) {
                      e.preventDefault();
                      return;
                    }
                    onDeleteAction?.(course);
                  }}
                >
                  Delete
                </AlertDialogAction>
              </ConfirmFooter>
            </ConfirmContent>
          </AlertDialog>

          <DialogContent onClick={(e) => e.stopPropagation()}>
            <DialogHeader>
              <DialogTitle>{mode === "edit" ? "Edit course" : "Clone course"}</DialogTitle>
            </DialogHeader>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor={`course-name-${course.id}`}>Name</Label>
                <Input
                  id={`course-name-${course.id}`}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Intro to AI"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`course-description-${course.id}`}>Description</Label>
                <Textarea
                  id={`course-description-${course.id}`}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional short description"
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isDisabled}>
                  {isSubmitting ? "Wait..." : mode === "edit" ? "Save" : "Clone"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <CardHeader className="flex-1 flex flex-col items-start">
        <CardTitle>{course.name}</CardTitle>
        {course.description && <CardDescription>{course.description}</CardDescription>}
      </CardHeader>
      <CardFooter>
        {/* TODO: fetch name and number of assignments? seems expensive... */}
        Instructor: {String(course.instructor_id)}
      </CardFooter>
    </Card>
  );
}

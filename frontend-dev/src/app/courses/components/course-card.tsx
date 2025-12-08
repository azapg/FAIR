
import {Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MoreVertical } from "lucide-react";
import type { Course } from "@/hooks/use-courses";
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
import { useTranslation } from "react-i18next";

export type CourseCardProps = {
  course: Course;
  onClickAction?: (id: string) => void;
  onDeleteAction?: (course: Course) => void;
};

type Mode = "edit" | "clone";

export default function CourseCard({ course, onClickAction, onDeleteAction }: CourseCardProps) {
  const { user, isAuthenticated } = useAuth();
  const updateCourse = useUpdateCourse();
  const createCourse = useCreateCourse();
  const { t } = useTranslation();

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
        instructorId: user.id,
      });
    }
    setOpen(false);
  };

  return (
    <Card
      className="flex flex-col bg-amber-50 hover:bg-amber-100 dark:bg-amber-950 dark:hover:bg-amber-900  transition-colors relative cursor-pointer gap-3"
      onClick={() => onClickAction?.(course.id)}
    >
      <div className="absolute top-3 right-3 z-10" onClick={(e) => e.stopPropagation()}>
        <Dialog open={open} onOpenChange={setOpen}>
          <AlertDialog onOpenChange={(isOpen) => { if (!isOpen) setConfirmName(""); }}>
            <DropdownMenu modal={false}>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" tabIndex={0} aria-label={t("actions.courseActions")}>
                  <MoreVertical className="w-5 h-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DialogTrigger asChild>
                  <DropdownMenuItem onClick={setupEdit}>{t("common.edit")}</DropdownMenuItem>
                </DialogTrigger>
                <DialogTrigger asChild>
                  <DropdownMenuItem onClick={setupClone}>{t("common.clone")}</DropdownMenuItem>
                </DialogTrigger>
                <AlertDialogTrigger asChild>
                  <DropdownMenuItem className="text-red-600">{t("common.delete")}</DropdownMenuItem>
                </AlertDialogTrigger>
              </DropdownMenuContent>
            </DropdownMenu>

            <ConfirmContent onClick={(e) => e.stopPropagation()}>
              <ConfirmHeader>
                <ConfirmTitle>{t("courses.deleteCourse")}</ConfirmTitle>
                <AlertDialogDescription>
                  {t("courses.deleteConfirmation")}
                  <span className="font-medium"> {course.name}</span>
                </AlertDialogDescription>
              </ConfirmHeader>
              <div className="space-y-2">
                <Label htmlFor={`confirm-name-${course.id}`}>{t("courses.courseName")}</Label>
                <Input
                  id={`confirm-name-${course.id}`}
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  placeholder={course.name}
                  autoFocus
                />
              </div>
              <ConfirmFooter>
                <AlertDialogCancel onClick={(e) => e.stopPropagation()}>{t("common.cancel")}</AlertDialogCancel>
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
                  {t("common.delete")}
                </AlertDialogAction>
              </ConfirmFooter>
            </ConfirmContent>
          </AlertDialog>

          <DialogContent onClick={(e) => e.stopPropagation()}>
            <DialogHeader>
              <DialogTitle>{mode === "edit" ? t("courses.editCourse") : t("courses.cloneCourse")}</DialogTitle>
            </DialogHeader>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor={`course-name-${course.id}`}>{t("courses.name")}</Label>
                <Input
                  id={`course-name-${course.id}`}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("courses.namePlaceholder")}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`course-description-${course.id}`}>{t("courses.description")}</Label>
                <Textarea
                  id={`course-description-${course.id}`}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("courses.descriptionPlaceholder")}
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isDisabled}>
                  {isSubmitting ? t("common.wait") : mode === "edit" ? t("common.save") : t("common.clone")}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <CardHeader className="flex-1 flex flex-col items-start">
        <CardTitle>{course.name}</CardTitle>
      </CardHeader>
      <CardContent>
        {course.description && <CardDescription>{course.description}</CardDescription>}
      </CardContent>
      <CardFooter>
        <span className="text-sm text-muted-foreground">
          {t("courses.by")} {course.instructorName}
          {course.assignmentsCount > 0 && ` • ${course.assignmentsCount} ${course.assignmentsCount > 1 ? t("courses.assignments") : t("courses.assignment")}`}
        </span>
      </CardFooter>
    </Card>
  );
}

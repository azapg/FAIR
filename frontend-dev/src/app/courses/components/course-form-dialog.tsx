import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export type CourseFormMode = "create" | "edit" | "clone";

export type CourseFormDialogProps = {
  open: boolean;
  onOpenChangeAction: (open: boolean) => void;
  mode: CourseFormMode;
  name: string;
  description: string;
  onNameChangeAction: (value: string) => void;
  onDescriptionChangeAction: (value: string) => void;
  onSubmitAction: (e: React.FormEvent) => void;
  isSubmitting?: boolean;
  isDisabled?: boolean;
  trigger?: ReactNode;
};

export default function CourseFormDialog({
  open,
  onOpenChangeAction,
  mode,
  name,
  description,
  onNameChangeAction,
  onDescriptionChangeAction,
  onSubmitAction,
  isSubmitting = false,
  isDisabled = false,
  trigger,
}: CourseFormDialogProps) {
  const { t } = useTranslation();
  
  const title = mode === "edit" 
    ? t("courses.editCourse") 
    : mode === "clone" 
    ? t("courses.cloneCourse") 
    : t("courses.createCourse");
  
  const cta = isSubmitting 
    ? t("common.wait") 
    : mode === "edit" 
    ? t("common.save") 
    : mode === "clone" 
    ? t("common.clone") 
    : t("common.create");

  return (
    <Dialog open={open} onOpenChange={onOpenChangeAction}>
      {trigger ? <DialogTrigger asChild>{trigger}</DialogTrigger> : null}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmitAction} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="course-name">{t("courses.name")}</Label>
            <Input
              id="course-name"
              value={name}
              onChange={(e) => onNameChangeAction(e.target.value)}
              placeholder={t("courses.namePlaceholder")}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="course-description">{t("courses.description")}</Label>
            <Textarea
              id="course-description"
              value={description}
              onChange={(e) => onDescriptionChangeAction(e.target.value)}
              placeholder={t("courses.descriptionPlaceholder")}
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isDisabled}>
              {cta}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

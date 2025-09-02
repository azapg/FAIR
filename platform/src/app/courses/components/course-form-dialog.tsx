import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ReactNode } from "react";

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
  const title = mode === "edit" ? "Edit course" : mode === "clone" ? "Clone course" : "Create course";
  const cta = isSubmitting ? "Wait..." : mode === "edit" ? "Save" : mode === "clone" ? "Clone" : "Create";

  return (
    <Dialog open={open} onOpenChange={onOpenChangeAction}>
      {trigger ? <DialogTrigger asChild>{trigger}</DialogTrigger> : null}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmitAction} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="course-name">Name</Label>
            <Input
              id="course-name"
              value={name}
              onChange={(e) => onNameChangeAction(e.target.value)}
              placeholder="Intro to AI"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="course-description">Description</Label>
            <Textarea
              id="course-description"
              value={description}
              onChange={(e) => onDescriptionChangeAction(e.target.value)}
              placeholder="Optional short description"
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

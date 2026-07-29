import {FormEvent, useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {Assignment, UpdateAssignmentInput, useUpdateAssignment} from "@/hooks/use-assignments";
import {CreateAssignmentForm, Grade} from "@/app/courses/tabs/assignments/assignments";
import {useTranslation} from "react-i18next";

interface EditAssignmentDialogProps {
  assignment: Assignment | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssignmentUpdated?: (assignment: Assignment) => void;
}

export function EditAssignmentDialog({
  assignment,
  open,
  onOpenChange,
  onAssignmentUpdated,
}: EditAssignmentDialogProps) {
  const {t} = useTranslation();
  const [form, setForm] = useState<CreateAssignmentForm>({
    title: "",
    description: "",
    dueDate: "",
    gradeValue: "",
  });
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const {mutateAsync: updateAssignment, isPending} = useUpdateAssignment();

  useEffect(() => {
    if (!assignment) return;
    const grade = assignment.maxGrade;
    const deadline = assignment.deadline
      ? assignment.deadline.slice(0, 10)
      : "";
    setForm({
      title: assignment.title,
      description: assignment.description ?? "",
      dueDate: deadline,
      gradeValue: grade?.value != null ? String(grade.value) : "",
    });
    setSubmissionError(null);
  }, [assignment, open]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!assignment) return;
    setSubmissionError(null);

    const points = Number(form.gradeValue);
    if (!Number.isFinite(points) || points <= 0) {
      setSubmissionError(t("assignments.pointsRequired"));
      return;
    }
    const totalPoints: Grade = {type: "points", value: points};

    const payload: UpdateAssignmentInput = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      deadline: form.dueDate || null,
      maxGrade: totalPoints,
    };

    try {
      const updated = await updateAssignment({
        id: assignment.id,
        data: payload,
      });
      onAssignmentUpdated?.(updated);
      onOpenChange(false);
    } catch (err: any) {
      let msg = t("assignments.failedToUpdate");
      if (err?.response?.data?.detail) {
        msg = err.response.data.detail;
      } else if (err?.message) {
        msg = err.message;
      }
      setSubmissionError(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>{t("assignments.editAssignment")}</DialogTitle>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-2">
            <Label htmlFor="title">{t("assignments.titleLabel")}</Label>
            <Input
              id="title"
              value={form.title}
              onChange={e => setForm(f => ({...f, title: e.target.value}))}
              required
              placeholder={t("assignments.titlePlaceholder")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="description">{t("assignments.description")}</Label>
            <Textarea
              id="description"
              value={form.description}
              onChange={e => setForm(f => ({...f, description: e.target.value}))}
              placeholder={t("assignments.descriptionPlaceholder")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="due">{t("assignments.dueDate")}</Label>
            <Input
              id="due"
              type="date"
              value={form.dueDate}
              onChange={e => setForm(f => ({...f, dueDate: e.target.value}))}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="gradeValue">{t("assignments.totalPoints")}</Label>
            <Input
              id="gradeValue"
              type="number"
              min="0"
              step="any"
              value={form.gradeValue}
              onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
              placeholder="e.g., 100"
              required
            />
          </div>

          {submissionError ? (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md border border-red-200">
              {submissionError}
            </div>
          ) : null}

          <DialogFooter>
            <Button type="submit" disabled={isPending || !assignment}>
              {isPending ? t("common.save") : t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

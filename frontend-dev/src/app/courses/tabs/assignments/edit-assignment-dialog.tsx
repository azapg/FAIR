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
    gradeType: "",
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
      gradeType: grade?.type ?? "",
      gradeValue: grade?.value != null ? String(grade.value) : "",
    });
    setSubmissionError(null);
  }, [assignment, open]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!assignment) return;
    setSubmissionError(null);

    let totalPoints: Grade | undefined = undefined;
    if (form.gradeType) {
      switch (form.gradeType) {
        case "points":
        case "percentage": {
          const num = Number(form.gradeValue);
          if (Number.isFinite(num)) {
            totalPoints = {type: form.gradeType, value: num};
          }
          break;
        }
        case "letter":
          if (form.gradeValue.trim()) {
            totalPoints = {type: "letter", value: form.gradeValue.trim()};
          }
          break;
        case "pass_fail":
          totalPoints = {type: "pass_fail", value: form.gradeValue === "pass"};
          break;
      }
    }

    const payload: UpdateAssignmentInput = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      deadline: form.dueDate || null,
      maxGrade: totalPoints ?? null,
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
            <Label htmlFor="gradeType">{t("assignments.gradingType")}</Label>
            <select
              id="gradeType"
              className="w-full rounded-md border px-3 py-2 text-sm"
              value={form.gradeType}
              onChange={e =>
                setForm(f => ({
                  ...f,
                  gradeType: e.target.value as Grade["type"] | "",
                  gradeValue: "",
                }))
              }
            >
              <option value="">{t("assignments.none")}</option>
              <option value="points">{t("assignments.points")}</option>
              <option value="percentage">{t("assignments.percentage")}</option>
              <option value="letter">{t("assignments.letter")}</option>
              <option value="pass_fail">{t("assignments.passFail")}</option>
            </select>
          </div>

          {form.gradeType === "points" || form.gradeType === "percentage" ? (
            <div className="grid gap-2">
              <Label htmlFor="gradeValue">
                {form.gradeType === "points" ? t("assignments.points") : t("assignments.percentage")}
              </Label>
              <Input
                id="gradeValue"
                type="number"
                step="any"
                value={form.gradeValue}
                onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                placeholder={form.gradeType === "points" ? "e.g., 100" : "e.g., 10"}
              />
            </div>
          ) : form.gradeType === "letter" ? (
            <div className="grid gap-2">
              <Label htmlFor="gradeLetter">{t("assignments.letterGrade")}</Label>
              <Input
                id="gradeLetter"
                value={form.gradeValue}
                onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                placeholder="e.g., A+"
              />
            </div>
          ) : form.gradeType === "pass_fail" ? (
            <div className="grid gap-2">
              <Label htmlFor="pf">{t("assignments.result")}</Label>
              <select
                id="pf"
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={form.gradeValue}
                onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
              >
                <option value="">{t("assignments.select")}</option>
                <option value="pass">{t("assignments.pass")}</option>
                <option value="fail">{t("assignments.fail")}</option>
              </select>
            </div>
          ) : null}

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

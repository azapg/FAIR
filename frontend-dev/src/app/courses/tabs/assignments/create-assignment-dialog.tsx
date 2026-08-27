import {useState, FormEvent, useRef} from "react";
import {Button} from "@/components/ui/button";
import {Dialog, DialogClose, DialogFooter, DialogHeader, DialogTitle, DialogTrigger} from "@/components/ui/dialog";
import { ResponsiveDialogContent } from "@/components/ui/responsive-dialog";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {Plus, FileText, X} from "lucide-react";
import { Assignment, useCreateAssignment, type CreateAssignmentInput } from "@/hooks/use-assignments";
import {CreateAssignmentForm, Grade} from "@/app/courses/tabs/assignments/assignments";
import {useTranslation} from "react-i18next";
import { DOCS_BASE_URL } from "@/lib/constants";

interface CreateAssignmentDialogProps {
  courseId?: string;
  onAssignmentCreated: (assignment: Assignment) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  showTrigger?: boolean;
}

interface FileItem {
  file: File;
  id: string;
}

export function CreateAssignmentDialog({
  courseId,
  onAssignmentCreated,
  open: controlledOpen,
  onOpenChange,
  showTrigger = true,
}: CreateAssignmentDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = (next: boolean) => {
    if (controlledOpen === undefined) {
      setInternalOpen(next);
    }
    onOpenChange?.(next);
  };
  const [form, setForm] = useState<CreateAssignmentForm>({
    title: "",
    description: "",
    dueDate: "",
    gradeValue: "100",
  });

  const [files, setFiles] = useState<FileItem[]>([]);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const {t} = useTranslation();

  const { mutateAsync: createAssignment, isPending } = useCreateAssignment();

  const resetForm = () => {
    setForm({title: "", description: "", dueDate: "", gradeValue: "100"});
    setFiles([]);
    setSubmissionError(null);
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) resetForm();
  };

  const handleFilePick = (fileList: FileList | null) => {
    if (!fileList) return;
    
    const newFiles: FileItem[] = Array.from(fileList).map(file => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random()}`,
    }));
    
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmissionError(null);
    
    if (!form.title.trim()) {
      setSubmissionError(t("assignments.titleRequired"));
      return;
    }

    const points = Number(form.gradeValue);
    if (!Number.isFinite(points) || points <= 0) {
      setSubmissionError(t("assignments.pointsRequired"));
      return;
    }
    const totalPoints: Grade = {type: "points", value: points};

    try {
      if (!courseId) {
        throw new Error(t("assignments.courseIdRequired"));
      }

      const payload: CreateAssignmentInput = {
        courseId: courseId,
        title: form.title.trim(),
        description: form.description.trim() || null,
        deadline: form.dueDate || null,
        maxGrade: totalPoints,
        files: files.map(f => f.file),
      };
      
      const created = await createAssignment(payload);

      onAssignmentCreated(created);
      setOpen(false);
      resetForm();
    } catch (err: any) {
      let msg = t("assignments.failedToCreate");
      if (err?.response?.data) {
        const data = err.response.data;
        if (data?.detail && typeof data.detail === "string") {
          msg = data.detail;
        } else if (data?.message && typeof data.message === "string") {
          msg = data.message;
        } else if (data?.errors) {
          try {
            msg = Array.isArray(data.errors) ? data.errors.join("; ") : JSON.stringify(data.errors);
          } catch {
            msg = String(data.errors);
          }
        }
      } else if (err?.message) {
        msg = err.message;
      }
      setSubmissionError(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {showTrigger && (
        <DialogTrigger asChild>
          <Button>
            <Plus className="mr-2"/>
            {t("common.create")}
          </Button>
        </DialogTrigger>
      )}
      <ResponsiveDialogContent className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden sm:max-w-2xl">
        <DialogHeader className="shrink-0 pb-4">
          <DialogTitle>{t("assignments.newAssignment")}</DialogTitle>
        </DialogHeader>
        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={handleSubmit}
        >
          <div
            data-slot="assignment-form-scroll"
            className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto pr-3"
          >
            <div className="grid gap-4">
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
                  className="min-h-28 max-h-64 resize-y overflow-y-auto"
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

              <div className="grid gap-2">
                <h2 className="text-muted-foreground text-sm">{t("assignments.resources")}</h2>
                <div className="flex flex-row flex-wrap items-center gap-2">
                  {files.map((item) => (
                    <Button
                      key={item.id}
                      variant="secondary"
                      size="sm"
                      type="button"
                      className="flex items-center gap-1"
                    >
                      <FileText className="h-4 w-4" />
                      <span className="max-w-[200px] truncate">{item.file.name}</span>
                      <X
                        className="ml-1 h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => removeFile(item.id)}
                      />
                    </Button>
                  ))}
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    multiple
                    onChange={(e) => {
                      handleFilePick(e.target.files);
                      e.currentTarget.value = "";
                    }}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    title={t("assignments.addResources")}
                  >
                    <Plus />
                  </Button>
                </div>
              </div>

              {submissionError ? (
                <div className="text-sm text-red-600 rounded-md border border-red-200 bg-red-50 p-3">
                  {submissionError}
                </div>
              ) : null}
            </div>
          </div>

          <DialogFooter className="shrink-0 border-t pt-4">
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isPending}>
                {t("common.cancel")}
              </Button>
            </DialogClose>
            <Button type="submit" disabled={isPending}>
              {isPending ? t("assignments.creating") : t("common.add")}
            </Button>
          </DialogFooter>
        </form>
      </ResponsiveDialogContent>
    </Dialog>
  );
}

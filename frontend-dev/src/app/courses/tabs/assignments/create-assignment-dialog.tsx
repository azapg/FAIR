import {useState, FormEvent, useRef} from "react";
import {Button} from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Textarea} from "@/components/ui/textarea";
import {Plus, FileText, X} from "lucide-react";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import { Assignment, useCreateAssignment, type CreateAssignmentInput } from "@/hooks/use-assignments";
import {CreateAssignmentForm, Grade} from "@/app/courses/tabs/assignments/assignments";

interface CreateAssignmentDialogProps {
  courseId?: string;
  onAssignmentCreated: (assignment: Assignment) => void;
}

interface FileItem {
  file: File;
  id: string;
}

export function CreateAssignmentDialog({ courseId, onAssignmentCreated }: CreateAssignmentDialogProps) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<CreateAssignmentForm>({
    title: "",
    description: "",
    dueDate: "",
    gradeType: "",
    gradeValue: "",
  });

  const [files, setFiles] = useState<FileItem[]>([]);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const { mutateAsync: createAssignment, isPending } = useCreateAssignment();

  const resetForm = () => {
    setForm({title: "", description: "", dueDate: "", gradeType: "", gradeValue: ""});
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
      setSubmissionError("Title is required");
      return;
    }

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
          totalPoints = { type: "pass_fail", value: form.gradeValue === "pass" };
          break;
      }
    }

    try {
      if (!courseId) {
        throw new Error("Course ID is required");
      }

      const payload: CreateAssignmentInput = {
        courseId: courseId,
        title: form.title.trim(),
        description: form.description.trim() || null,
        deadline: form.dueDate || null,
        maxGrade: totalPoints ?? null,
        files: files.map(f => f.file),
      };
      
      const created = await createAssignment(payload);

      onAssignmentCreated(created);
      setOpen(false);
      resetForm();
    } catch (err: any) {
      let msg = "Failed to create assignment.";
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
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2"/>
          Create
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[60%] h-[90%]">
        <DialogHeader>
          <DialogTitle>New Assignment</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-full w-full">
          <form
            className="grid gap-4"
            onSubmit={handleSubmit}
          >
            <div className="grid gap-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={form.title}
                onChange={e => setForm(f => ({...f, title: e.target.value}))}
                required
                placeholder="e.g., Essay 2"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={form.description}
                onChange={e => setForm(f => ({...f, description: e.target.value}))}
                placeholder="Brief details..."
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="due">Due date</Label>
              <Input
                id="due"
                type="date"
                value={form.dueDate}
                onChange={e => setForm(f => ({...f, dueDate: e.target.value}))}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="gradeType">Grading type</Label>
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
                <option value="">None</option>
                <option value="points">Points</option>
                <option value="percentage">Percentage</option>
                <option value="letter">Letter</option>
                <option value="pass_fail">Pass/Fail</option>
              </select>
            </div>

            {form.gradeType === "points" || form.gradeType === "percentage" ? (
              <div className="grid gap-2">
                <Label htmlFor="gradeValue">
                  {form.gradeType === "points" ? "Points" : "Percentage"}
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
                <Label htmlFor="gradeLetter">Letter grade</Label>
                <Input
                  id="gradeLetter"
                  value={form.gradeValue}
                  onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                  placeholder="e.g., A+"
                />
              </div>
            ) : form.gradeType === "pass_fail" ? (
              <div className="grid gap-2">
                <Label htmlFor="pf">Result</Label>
                <select
                  id="pf"
                  className="w-full rounded-md border px-3 py-2 text-sm"
                  value={form.gradeValue}
                  onChange={e => setForm(f => ({...f, gradeValue: e.target.value}))}
                >
                  <option value="">Select</option>
                  <option value="pass">Pass</option>
                  <option value="fail">Fail</option>
                </select>
              </div>
            ) : null}

            <div className="grid gap-2">
              <h2 className="text-muted-foreground text-sm">Resources</h2>
              <div className="flex flex-row flex-wrap gap-2 items-center">
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
                      className="h-3 w-3 ml-1 cursor-pointer hover:text-destructive"
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
                  title="Add resources"
                >
                  <Plus />
                </Button>
              </div>
            </div>

            {submissionError ? (
              <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md border border-red-200">
                {submissionError}
              </div>
            ) : null}

            <DialogFooter>
              <Button type="submit" disabled={isPending}>
                {isPending ? "Creating..." : "Add"}
              </Button>
            </DialogFooter>
          </form>

          <ScrollBar />
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
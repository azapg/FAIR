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
import {Plus, FileText, Hourglass} from "lucide-react";
import {ScrollArea, ScrollBar} from "@/components/ui/scroll-area";
import { useCreateArtifact, type CreateArtifactInput } from "@/hooks/use-artifacts";
import { useCreateAssignment, type CreateAssignmentInput } from "@/hooks/use-assignments";
import {CreateAssignmentForm, ArtifactChip, Grade, Assignment} from "@/app/courses/tabs/assignments/assignments";

interface CreateAssignmentDialogProps {
  courseId?: string;
  onAssignmentCreated: (assignment: Assignment) => void;
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

  // Artifacts state for the creation dialog
  const [artifactChips, setArtifactChips] = useState<ArtifactChip[]>([]);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const { mutateAsync: createArtifact } = useCreateArtifact();
  const { mutateAsync: createAssignment } = useCreateAssignment();

  const resetForm = () => {
    setForm({title: "", description: "", dueDate: "", gradeType: "", gradeValue: ""});
    setArtifactChips([]);
    setSubmissionError(null);
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) resetForm();
  };

  // Infer mime and artifact_type for a limited set of document extensions
  function getDocMeta(fileName: string, fallbackMime?: string): { mime: string; artifact_type: string } | null {
    const ext = fileName.toLowerCase().split(".").pop() || "";
    switch (ext) {
      case "pdf":
        return { mime: "application/pdf", artifact_type: "document/pdf" };
      case "txt":
        return { mime: "text/plain", artifact_type: "document/text" };
      case "doc":
        return { mime: "application/msword", artifact_type: "document/word" };
      case "docx":
        return { mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", artifact_type: "document/word" };
      default: {
        // Try a conservative fallback if the browser supplied a recognizable text/pdf type
        if (fallbackMime?.includes("pdf")) return { mime: "application/pdf", artifact_type: "document/pdf" };
        if (fallbackMime?.includes("text")) return { mime: "text/plain", artifact_type: "document/text" };
        return null;
      }
    }
  }

  async function addArtifactFromFile(file: File) {
    const meta = getDocMeta(file.name, file.type);
    if (!meta) {
      setArtifactChips(prev => [
        ...prev,
        {
          title: file.name,
          fileName: file.name,
          mime: "unknown/unknown",
          artifact_type: "document/unknown",
          storage_type: "local",
          storage_path: `local://${file.name}`,
          status: "error",
          error: "Unsupported file type. Only .txt, .pdf, .doc, .docx are allowed.",
        },
      ]);
      return;
    }

    const draft: ArtifactChip = {
      title: file.name,
      fileName: file.name,
      mime: meta.mime,
      artifact_type: meta.artifact_type,
      storage_type: "local",
      storage_path: `local://${file.name}`,
      status: "uploading",
    };
    setArtifactChips(prev => [...prev, draft]);

    try {
      const payload: CreateArtifactInput = {
        title: draft.title,                 // could be beautified or derived later
        artifact_type: draft.artifact_type, // e.g., document/pdf, document/text, document/word
        mime: draft.mime,                   // limited set handled above
        storage_type: draft.storage_type,   // local
        storage_path: draft.storage_path,   // e.g., local://document.pdf
        meta: { original_name: file.name },
      };
      const created = await createArtifact(payload);
      setArtifactChips(prev =>
        prev.map(a =>
          a === draft
            ? { ...a, id: created.id, status: "uploaded" }
            : a
        )
      );
    } catch (e: any) {
      setArtifactChips(prev =>
        prev.map(a =>
          a === draft
            ? { ...a, status: "error", error: e?.message ?? "Failed to upload artifact" }
            : a
        )
      );
    }
  }

  const handleFilePick = (files: FileList | null) => {
    const file = files?.[0];
    if (file) addArtifactFromFile(file).then();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmissionError(null); // clear previous
    if (!form.title.trim()) return;

    // Prevent submission while artifacts are still uploading
    if (artifactChips.some(a => a.status === "uploading")) {
      setSubmissionError("Please wait for all resources to finish uploading before submitting.");
      return;
    }

    // Map grading to backend shape (only numeric max_grade supported for now)
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

    const artifactIds = artifactChips
      .filter(a => a.id && a.status === "uploaded")
      .map(a => a.id!);

    // Try to persist via API when possible
    try {
      if (courseId) {
        const payload: CreateAssignmentInput = {
          course_id: courseId,
          title: form.title.trim(),
          description: form.description.trim() || null,
          deadline: form.dueDate || null,
          max_grade: totalPoints ?? null,
          artifacts: artifactIds,
        };
        await createAssignment(payload);
      }
    } catch (err: any) {
      let msg = "Failed to create assignment.";
      if (err?.response) {
        const data = err.response.data;
        if (data?.message && typeof data.message === "string") {
          msg = data.message;
        } else if (data?.errors) {
          try {
            msg = Array.isArray(data.errors) ? data.errors.join("; ") : JSON.stringify(data.errors);
          } catch {
            msg = String(data.errors);
          }
        } else {
          try {
            msg = JSON.stringify(data);
          } catch {
            msg = String(data);
          }
        }
      } else if (err?.message) {
        msg = err.message;
      }
      setSubmissionError(msg);
      // stop here - do not close dialog or reset form on error
      return;
    }

    // On success continue with local UI behavior
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Date.now().toString();

    const now = new Date();
    const newAssignment: Assignment = {
      id,
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      dueDate: form.dueDate ? new Date(form.dueDate) : undefined,
      totalPoints,
      createdAt: now,
      updatedAt: now,
    };

    onAssignmentCreated(newAssignment);
    setOpen(false);
    resetForm();
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

            {/* Resources (artifacts) - styled like demo/assignment/page */}
            <div className="grid gap-2">
              <h2 className="text-muted-foreground text-sm">Resources</h2>
              <div className="flex flex-row flex-wrap gap-1 items-center">
                {artifactChips.map((a, idx) => (
                  <Button key={`${a.fileName}-${idx}`} variant="secondary" size="sm" type="button">
                    {a.status === "uploading" ? <Hourglass className="mr-1 h-4 w-4" /> : <FileText className="mr-1 h-4 w-4" />}
                    {a.title}
                    {a.status === "error" ? <span className="ml-2 text-red-600">(error)</span> : null}
                  </Button>
                ))}
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".txt,.pdf,.doc,.docx"
                  onChange={(e) => {
                    handleFilePick(e.target.files);
                    // allow re-selecting the same file
                    e.currentTarget.value = "";
                  }}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  title="Add resource"
                >
                  <Plus />
                </Button>
              </div>
            </div>

            {/* show server / submission errors */}
            {submissionError ? (
              <div className="text-sm text-red-600">{submissionError}</div>
            ) : null}

            <DialogFooter>
              <Button type="submit">Add</Button>
            </DialogFooter>
          </form>

          <ScrollBar />
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
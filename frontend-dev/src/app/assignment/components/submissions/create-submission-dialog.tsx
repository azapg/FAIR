import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {LoaderIcon, PlusIcon} from "lucide-react";
import {useState} from "react";
import api from "@/lib/api";

type CreateSubmissionDialogProps = {
  assignmentId: string;
}

export function CreateSubmissionDialog({ assignmentId }: CreateSubmissionDialogProps) {
  const [username, setUsername] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const handleCreate = () => {
    setIsLoading(true);

    const formData = new FormData();
    if (files) {
      Array.from(files).forEach((file) => {
        formData.append(`files`, file);
      })

      api.post("/artifacts", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }).then(async (response) => {
        const artifactIds = response.data.map((artifact: any) => artifact.id);
        await api.post("/submissions", {
          assignment_id: assignmentId,
          submitter: username,
          artifact_ids: artifactIds,
        });
        setIsLoading(false);
        setOpen(false);
      }).catch((error) => {
        console.error("Error creating artifacts:", error);
        setIsLoading(false);
      });
    } else {
      api.post("/submissions", {
        assignment_id: assignmentId,
        submitter: username,
        artifact_ids: [],
      }).then(() => {
        setIsLoading(false);
        setOpen(false);
      }).catch((error) => {
        console.error("Error creating submission:", error);
        setIsLoading(false);
      });
    }


  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button><PlusIcon/> Add</Button>
      </DialogTrigger>
      <DialogContent className={""}>
        <DialogHeader>
          <DialogTitle>Add a submission</DialogTitle>
          <DialogDescription>Create a synthetic submission for a student</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Student Name</label>
            <Input
              placeholder="Allan Zapata"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Files</label>
            <Input
              type="file"
              multiple
              accept=".pdf"
              onChange={(e) => setFiles(e.target.files)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} disabled={!username.trim() || isLoading}>{isLoading ? <><LoaderIcon className={"animate-spin"}/>Creating...</> : <>Create</>}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
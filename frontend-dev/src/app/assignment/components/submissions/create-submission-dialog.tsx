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
import {useCreateSubmission} from "@/hooks/use-submissions";

type CreateSubmissionDialogProps = {
  assignmentId: string;
}

export function CreateSubmissionDialog({ assignmentId }: CreateSubmissionDialogProps) {
  const [username, setUsername] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [open, setOpen] = useState(false);
  
  const createSubmission = useCreateSubmission();

  const handleCreate = async () => {
    try {
      await createSubmission.mutateAsync({
        assignment_id: assignmentId,
        submitter_name: username,
        files: files ? Array.from(files) : undefined,
      });
      
      setUsername("");
      setFiles(null);
      setOpen(false);
    } catch (error: any) {
      console.error("Error creating submission:", error);
      alert(error.response?.data?.detail || "Failed to create submission");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm"><PlusIcon/> Add</Button>
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
          <Button 
            onClick={handleCreate} 
            disabled={!username.trim() || createSubmission.isPending}
          >
            {createSubmission.isPending ? (
              <>
                <LoaderIcon className={"animate-spin"}/>
                Creating...
              </>
            ) : (
              <>Create</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
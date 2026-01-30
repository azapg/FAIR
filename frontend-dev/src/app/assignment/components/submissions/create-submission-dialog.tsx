import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {LoaderIcon} from "lucide-react";
import {useState} from "react";
import {useCreateSubmission} from "@/hooks/use-submissions";
import {useTranslation} from "react-i18next";

type CreateSubmissionDialogProps = {
  assignmentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateSubmissionDialog({ assignmentId, open, onOpenChange }: CreateSubmissionDialogProps) {
  const [username, setUsername] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const {t} = useTranslation();
  
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
      onOpenChange(false);
    } catch (error: any) {
      console.error("Error creating submission:", error);
      alert(error.response?.data?.detail || t("submissions.failedToCreate"));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={""}>
        <DialogHeader>
          <DialogTitle>{t("submissions.addSubmission")}</DialogTitle>
          <DialogDescription>{t("submissions.createSynthetic")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">{t("submissions.studentName")}</label>
            <Input
              placeholder="Allan Zapata"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">{t("submissions.files")}</label>
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
                {t("submissions.creating")}
              </>
            ) : (
              <>{t("common.create")}</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Submission } from "@/hooks/use-submissions"

interface SubmissionSheetProps {
  submission: Submission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SubmissionSheet({ submission, open, onOpenChange }: SubmissionSheetProps) {
  if (!submission) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[700px] sm:max-w-[700px]">
        <SheetHeader>
          <SheetTitle>Submission Details</SheetTitle>
          <SheetDescription>
            Details for submission by {submission.submitter?.name}
          </SheetDescription>
        </SheetHeader>
        <div className="grid flex-1 auto-rows-min gap-6 px-4">
          <div className="grid gap-3">
            <Label>Submitter Name</Label>
            <p>{submission.submitter?.name}</p>
          </div>
          <div className="grid gap-3">
            <Label>Submitter Email</Label>
            <p>{submission.submitter?.email}</p>
          </div>
          <div className="grid gap-3">
            <Label>Status</Label>
            <p>{submission.status}</p>
          </div>
          {submission.draftScore != null && (
            <div className="grid gap-3">
              <Label>Draft Score</Label>
              <p>{submission.draftScore}</p>
            </div>
          )}
          {submission.draftFeedback && (
            <div className="grid gap-3">
              <Label>Draft Feedback</Label>
              <p>{submission.draftFeedback}</p>
            </div>
          )}
        </div>
        <SheetFooter>
          <SheetClose asChild>
            <Button variant="outline">Close</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}

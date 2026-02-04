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
import {
  PropertiesDisplay,
  Property,
  PropertyLabel,
  PropertyValue,
} from "@/components/properties-display";

import { Submission } from "@/hooks/use-submissions"
import { SubmissionStatusLabel, InlineEditableScore, InlineEditableFeedback, formatShortDate } from "./submissions";
import { useTranslation } from "react-i18next";

interface SubmissionSheetProps {
  submission: Submission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SubmissionSheet({ submission, open, onOpenChange }: SubmissionSheetProps) {
  const { i18n } = useTranslation();
  if (!submission) return null;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[1000px] sm:max-w-[1000px]">
        <div className="flex flex-row h-full">
          <div className="w-2/3">
            <SheetHeader>
              <SheetTitle className="text-3xl">{submission.submitter?.name}</SheetTitle>
            </SheetHeader>
            <div className="grid flex-1 auto-rows-min gap-6 px-4">
              <PropertiesDisplay scroll gapX={2.5}>
                <Property>
                  <PropertyLabel>Status</PropertyLabel>
                  <PropertyValue><SubmissionStatusLabel status={submission.status} /></PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>Grade</PropertyLabel>
                  <PropertyValue><InlineEditableScore submission={submission} /></PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>Feedback</PropertyLabel>
                  <PropertyValue><InlineEditableFeedback submission={submission} /></PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>Turned in</PropertyLabel>
                  <PropertyValue>{formatShortDate(new Date(submission.submittedAt), i18n.language)}</PropertyValue>
                </Property>
              </PropertiesDisplay>
            </div>
          </div>
          <div className="w-1/3">
            <h1>Attachments</h1>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

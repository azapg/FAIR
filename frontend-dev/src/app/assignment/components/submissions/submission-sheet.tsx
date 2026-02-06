import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { ArrowUpRight } from "lucide-react";
import { getIconForMime } from "@/lib/utils";
import {
  PropertiesDisplay,
  Property,
  PropertyLabel,
  PropertyValue,
} from "@/components/properties-display";

import { Submission, useSubmissionTimeline } from "@/hooks/use-submissions";
import {
  SubmissionStatusLabel,
  InlineEditableScore,
  InlineEditableFeedback,
  formatShortDate,
} from "./submissions";
import { useTranslation } from "react-i18next";
import { useIsMobile } from "@/hooks/use-mobile";
import SubmissionTimeline from "@/components/submission-timeline";
import { ScrollArea } from "@/components/ui/scroll-area";

interface SubmissionSheetProps {
  submission: Submission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  focusOn?: "feedback" | null;
}

export function SubmissionSheet({
  submission,
  open,
  onOpenChange,
  focusOn,
}: SubmissionSheetProps) {
  const { i18n, t } = useTranslation();
  const isMobile = useIsMobile();
  const { data: timeline } = useSubmissionTimeline(submission?.id);

  if (!submission) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        className="w-full h-9/10 md:h-full md:min-w-4/5 lg:min-w-1/3"
        side={isMobile ? "bottom" : "right"}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <ScrollArea className="overflow-y-auto">
          <div className="p-6 overflow-y-auto">
            <SheetTitle className="text-3xl font-extrabold pb-6">
              <span>{submission.submitter?.name}</span>
            </SheetTitle>
            <div className="grid flex-1 auto-rows-min gap-6">
              <PropertiesDisplay scroll gapX={7} className="items-start">
                <Property>
                  <PropertyLabel>Status</PropertyLabel>
                  <PropertyValue>
                    <SubmissionStatusLabel status={submission.status} />
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>Turned in</PropertyLabel>
                  <PropertyValue>
                    {formatShortDate(
                      new Date(submission.submittedAt),
                      i18n.language,
                    )}
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>Grade</PropertyLabel>
                  <PropertyValue>
                    <InlineEditableScore submission={submission} />
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>Feedback</PropertyLabel>
                  <PropertyValue>
                    <InlineEditableFeedback
                      submission={submission}
                      startInEditMode={focusOn === "feedback"}
                    />
                  </PropertyValue>
                </Property>
              </PropertiesDisplay>
              <h1 className="text-xl font-medium">Attachments</h1>
              <div className="flex flex-row gap-1 items-center">
                {submission.artifacts && submission.artifacts.length > 0 ? (
                  submission.artifacts.map((artifact) => {
                    const Icon = getIconForMime(artifact.mime);
                    return (
                      <Button
                        key={artifact.id}
                        variant={"secondary"}
                        size={"sm"}
                      >
                        <Icon />
                        {artifact.title}
                        <ArrowUpRight className="text-muted-foreground" />
                      </Button>
                    );
                  })
                ) : (
                  <>This submission doesn't include attachments.</>
                )}
              </div>
              <h1 className="text-xl font-medium">Timeline</h1>
              <SubmissionTimeline timeline={timeline} />
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

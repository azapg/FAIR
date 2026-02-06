import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
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
        className="w-full h-9/10 md:h-full md:min-w-4/5 lg:min-w-1/3 p-4 overflow-y-auto"
        side={isMobile ? "bottom" : "right"}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <SheetTitle className="text-4xl">
          {submission.submitter?.name}
        </SheetTitle>
        <div className="grid flex-1 auto-rows-min gap-6">
          <PropertiesDisplay scroll gapX={2.5}>
            <Property>
              <PropertyLabel>Status</PropertyLabel>
              <PropertyValue>
                <SubmissionStatusLabel status={submission.status} />
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

            <Property>
              <PropertyLabel>Turned in</PropertyLabel>
              <PropertyValue>
                {formatShortDate(
                  new Date(submission.submittedAt),
                  i18n.language,
                )}
              </PropertyValue>
            </Property>
          </PropertiesDisplay>
          <h1>Attachments</h1>
          <div className="flex flex-row gap-1 items-center">
            {submission.artifacts && submission.artifacts.length > 0 ? (
              submission.artifacts.map((artifact) => {
                const Icon = getIconForMime(artifact.mime);
                return (
                  <Button key={artifact.id} variant={"secondary"} size={"sm"}>
                    <Icon />
                    {artifact.title}
                    <ArrowUpRight className="text-muted-foreground" />
                  </Button>
                );
              })
            ) : (
              <></>
            )}
          </div>
          <h1>Timeline</h1>
          <SubmissionTimeline timeline={timeline}/>
        </div>
      </SheetContent>
    </Sheet>
  );
}

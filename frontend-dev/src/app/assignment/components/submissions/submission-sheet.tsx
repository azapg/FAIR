import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { ArrowUpRight, CircleCheck } from "lucide-react";
import { getIconForMime } from "@/lib/utils";
import {
  PropertiesDisplay,
  Property,
  PropertyLabel,
  PropertyValue,
} from "@/components/properties-display";

import {
  Submission,
  useSubmissionTimeline,
  useReturnSubmission,
} from "@/hooks/use-submissions";
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
  const returnSubmission = useReturnSubmission();

  if (!submission) return null;

  const hasDraft =
    submission.draftScore != null || submission.draftFeedback != null;
  const canReturn =
    hasDraft && submission.status !== "returned" && !returnSubmission.isPending;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        className="w-full h-9/10 md:h-full md:min-w-4/5 lg:min-w-1/3"
        side={isMobile ? "bottom" : "right"}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <ScrollArea className="overflow-y-auto">
          <div className="p-6 overflow-y-auto">
            <SheetTitle className="text-3xl font-extrabold pb-6 flex items-center justify-between">
              <span>{submission.submitter?.name}</span>
              <Button
                variant="secondary"
                disabled={!canReturn}
                onClick={() => returnSubmission.mutate(submission.id)}
              >
                <CircleCheck size={16} /> {t("submissions.returnAction")}
              </Button>
            </SheetTitle>
            <div className="grid flex-1 auto-rows-min gap-6">
              <PropertiesDisplay scroll gapX={7} className="items-start">
                <Property>
                  <PropertyLabel>{t("submissions.status")}</PropertyLabel>
                  <PropertyValue>
                    <SubmissionStatusLabel status={submission.status} />
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>{t("submissions.turnedIn")}</PropertyLabel>
                  <PropertyValue>
                    {formatShortDate(
                      new Date(submission.submittedAt),
                      i18n.language,
                    )}
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>{t("submissions.grade")}</PropertyLabel>
                  <PropertyValue>
                    <InlineEditableScore submission={submission} />
                  </PropertyValue>
                </Property>

                <Property>
                  <PropertyLabel>{t("submissions.feedback")}</PropertyLabel>
                  <PropertyValue>
                    <InlineEditableFeedback
                      submission={submission}
                      startInEditMode={focusOn === "feedback"}
                    />
                  </PropertyValue>
                </Property>
              </PropertiesDisplay>
              <h1 className="text-xl font-medium">
                {t("submissions.attachments")}
              </h1>
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
                  <>{t("submissions.noAttachments")}</>
                )}
              </div>
              <h1 className="text-xl font-medium">
                {t("submissions.timeline")}
              </h1>
              <SubmissionTimeline timeline={timeline} />
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

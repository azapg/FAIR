import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  ArrowUpRight,
  CircleCheck,
  Ellipsis,
  Maximize2,
  PanelBottomClose,
  PanelRightClose,
} from "lucide-react";
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
} from "@/app/assignment/components/submissions/submissions";
import { useTranslation } from "react-i18next";
import { useIsMobile } from "@/hooks/use-mobile";
import SubmissionTimeline from "@/components/submission-timeline";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

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
        className="w-full h-9/10 md:h-full md:min-w-4/5 lg:min-w-1/2 gap-0"
        side={isMobile ? "bottom" : "right"}
        onOpenAutoFocus={(e) => e.preventDefault()}
        showCloseButton={false}
      >

        <div className="w-full flex justify-between text-muted-foreground py-2 px-4">
          <div className="flex items-center">
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon-sm">
                {isMobile ? <PanelBottomClose /> : <PanelRightClose />}
              </Button>
            </SheetTrigger>
            <Button variant="ghost" size="icon-sm">
              <Maximize2 />
            </Button>
          </div>
          <div className="flex gap-2 items-center">
            <Button
              variant="secondary"
              disabled={!canReturn}
              onClick={() => returnSubmission.mutate(submission.id)}
            >
              <CircleCheck size={16} /> {t("submissions.returnAction")}
            </Button>
            <Button variant="ghost" size="icon-sm">
              <Ellipsis />
            </Button>
          </div>
        </div>

        <ScrollArea className="overflow-y-auto gap-6">
          <SheetHeader className="gap-3 px-8 md:px-12">
            <SheetTitle className="text-3xl font-medium">
              {submission.submitter?.name}
            </SheetTitle>
            <PropertiesDisplay scroll gapX={4} className="items-start">
              <Property>
                <PropertyLabel>{t("submissions.status")}</PropertyLabel>
                <PropertyValue>
                  <SubmissionStatusLabel status={submission.status} />
                </PropertyValue>
              </Property>

              <Property>
                <PropertyLabel>{t("submissions.turnedIn")}</PropertyLabel>
                <PropertyValue className="text-sm">
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
          </SheetHeader>

          <div className="grid flex-1 auto-rows-min gap-6 px-8 md:px-12">
            <Separator className="w-full" />
            <h1 className="text-xl font-medium">
              {t("submissions.attachments")}
            </h1>
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
                <>{t("submissions.noAttachments")}</>
              )}
            </div>
            <h1 className="text-xl font-medium">{t("submissions.timeline")}</h1>
            <SubmissionTimeline timeline={timeline} />
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

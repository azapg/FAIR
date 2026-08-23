import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import {
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
  hasUnpublishedDraft,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArtifactAction } from "@/components/artifact-action";
import { SubmissionComments } from "@/components/submission-comments";

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

  const canReturn =
    hasUnpublishedDraft(submission) && !returnSubmission.isPending;

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      direction={isMobile ? "bottom" : "right"}
      autoFocus={focusOn !== "feedback"}
    >
      <DrawerContent
        className="h-9/10 w-full gap-0 data-[vaul-drawer-direction=bottom]:max-h-[90vh] md:h-full md:min-w-4/5 lg:min-w-1/2"
      >
        <div className="w-full flex justify-between text-muted-foreground py-2 px-4">
          <div className="flex items-center">
            <DrawerClose asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t("submissions.closeDetails")}
              >
                {isMobile ? (
                  <PanelBottomClose aria-hidden="true" />
                ) : (
                  <PanelRightClose aria-hidden="true" />
                )}
              </Button>
            </DrawerClose>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("submissions.expandDetails")}
            >
              <Maximize2 aria-hidden="true" />
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
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("submissions.moreActions")}
            >
              <Ellipsis aria-hidden="true" />
            </Button>
          </div>
        </div>

        <ScrollArea className="overflow-y-auto gap-6">
          <DrawerHeader className="gap-3 px-8 md:px-12 text-left">
            <DrawerTitle className="text-3xl font-medium">
              {submission.submitter?.name}
            </DrawerTitle>
            <DrawerDescription className="sr-only">
              {t("submissions.detailsDescription")}
            </DrawerDescription>
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
          </DrawerHeader>

          <div className="px-8 md:px-12">
            <Tabs defaultValue="attachments" className="w-full">
              <TabsList className="w-full justify-start">
                <TabsTrigger value="attachments">
                  {t("submissions.attachments")}
                </TabsTrigger>
                <TabsTrigger value="timeline">
                  {t("submissions.timeline")}
                </TabsTrigger>
                <TabsTrigger value="comments">
                  {t("submissions.privateComments")}
                </TabsTrigger>
              </TabsList>
              <TabsContent value="attachments" className="py-3">
                <SubmissionAttachments artifacts={submission.artifacts} />
              </TabsContent>
              <TabsContent value="timeline" className="py-3">
                <SubmissionTimeline timeline={timeline} />
              </TabsContent>
              <TabsContent value="comments" className="py-3">
                <SubmissionComments submissionId={submission.id} />
              </TabsContent>
            </Tabs>
          </div>
        </ScrollArea>
      </DrawerContent>
    </Drawer>
  );
}

function SubmissionAttachments({
  artifacts,
}: {
  artifacts: Submission["artifacts"];
}) {
  const { t } = useTranslation();

  if (!artifacts || artifacts.length === 0) {
    return (
      <div className="text-muted-foreground">{t("submissions.noAttachments")}</div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {artifacts.map((artifact) => {
        const Icon = getIconForMime(artifact.mime);
        return (
          <ArtifactAction
            key={artifact.id}
            artifact={artifact}
            icon={Icon}
            variant="secondary"
            size="sm"
          />
        );
      })}
    </div>
  );
}

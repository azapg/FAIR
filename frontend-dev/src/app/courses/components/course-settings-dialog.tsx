import { useReleaseFeatures } from "@/hooks/use-release-features";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  coursesKeys,
  useUpdateCourse,
  type Course,
  type CourseDetail,
} from "@/hooks/use-courses";
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResponsiveDialogContent } from "@/components/ui/responsive-dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RunsTab } from "../tabs/runs-tab";
import { FlowsTab } from "../tabs/flows-tab";
import { CapabilitiesTab } from "../tabs/capabilities-tab";
import { ArtifactsTab } from "../tabs/artifacts-tab";
import type { Assignment } from "@/hooks/use-assignments";
import { CourseCopyDialog } from "./course-copy-dialog";

export type CourseSettingsSection =
  "general" | "enrollment" | "runs" | "flows" | "capabilities" | "artifacts";
const ADVANCED: { id: CourseSettingsSection; label: string }[] = [
  { id: "flows", label: "Flows" },
  { id: "runs", label: "Runs" },
  { id: "capabilities", label: "Capabilities" },
  { id: "artifacts", label: "Artifacts" },
];

export function CourseSettingsDialog({
  course,
  assignments,
  canEdit,
  enrollmentControls,
  initialSection = "general",
  onClose,
}: {
  course: Course | CourseDetail;
  assignments: Assignment[];
  canEdit: boolean;
  enrollmentControls?: ReactNode;
  initialSection?: CourseSettingsSection;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const flags = useReleaseFeatures();
  const advanced = ADVANCED.filter(
    (item) => flags.extensions || item.id === "artifacts",
  );
  const [requestedSection, setSection] = useState<CourseSettingsSection>(
    initialSection === "enrollment" && !enrollmentControls
      ? "general"
      : initialSection,
  );
  const [name, setName] = useState(course.name);
  const [description, setDescription] = useState(course.description ?? "");
  const [archiveConfirm, setArchiveConfirm] = useState(false);
  const [archivePending, setArchivePending] = useState(false);
  const [archiveError, setArchiveError] = useState(false);
  const updateCourse = useUpdateCourse();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const mainSections: { id: CourseSettingsSection; label: string }[] = [
    { id: "general", label: "General" },
    ...(enrollmentControls
      ? [{ id: "enrollment" as const, label: "Enrollment" }]
      : []),
  ];
  const selected =
    [...mainSections, ...advanced].find((s) => s.id === requestedSection) ??
    mainSections[0];
  const section = selected.id;

  async function changeArchive() {
    setArchivePending(true);
    setArchiveError(false);
    try {
      await api.post(
        `/courses/${course.id}/${course.isArchived ? "reopen" : "archive"}`,
      );
      await queryClient.invalidateQueries({ queryKey: coursesKeys.all });
      setArchiveConfirm(false);
      onClose();
      navigate(`/courses/${course.id}/stream`);
    } catch {
      setArchiveError(true);
      toast.error(
        `Could not ${course.isArchived ? "reopen" : "archive"} this course. Please try again.`,
      );
    } finally {
      setArchivePending(false);
    }
  }

  const navGroup = (label: string, sections: typeof ADVANCED) => (
    <div className="flex flex-col gap-2">
      <p className="hidden px-2 text-xs uppercase tracking-wide text-muted-foreground md:block">
        {label}
      </p>
      <div className="flex flex-wrap gap-1 md:flex-col">
        {sections.map((item) => (
          <button
            key={item.id}
            aria-current={section === item.id ? "page" : undefined}
            className={cn(
              "rounded-md px-2 py-1.5 text-left text-sm text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              section === item.id && "bg-muted font-medium text-foreground",
            )}
            onClick={() => setSection(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <>
      <Dialog
        open
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      >
        <ResponsiveDialogContent
          showCloseButton={false}
          className="!flex h-[90dvh] !w-[calc(100vw-2rem)] !max-w-[1200px] !flex-col gap-0 overflow-hidden p-0"
        >
          <DialogHeader className="sr-only">
            <DialogTitle>Course settings</DialogTitle>
            <DialogDescription>Manage {course.name}</DialogDescription>
          </DialogHeader>
          <div className="relative flex min-h-0 flex-1 flex-col md:grid md:grid-cols-[minmax(14rem,1fr)_minmax(0,46rem)_minmax(3.5rem,1fr)]">
            <DialogClose asChild>
              <Button
                variant="outline"
                size="icon"
                className="absolute right-4 top-4 rounded-full"
                aria-label="Close course settings"
              >
                <X />
              </Button>
            </DialogClose>
            <aside className="shrink-0 bg-muted/30 md:min-h-0">
              <ScrollArea className="h-full">
                <div className="ml-auto flex w-full flex-col gap-5 px-4 py-6 md:max-w-60">
                  <div className="pr-10">
                    <h2 className="text-base font-medium">Course settings</h2>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {course.name}
                    </p>
                  </div>
                  <nav
                    aria-label="Course settings"
                    className="flex flex-col gap-3 md:gap-5"
                  >
                    {navGroup("Course", mainSections)}
                    {navGroup("Advanced", advanced)}
                  </nav>
                </div>
              </ScrollArea>
            </aside>
            <ScrollArea className="min-h-0 flex-1">
              <div className="flex flex-col gap-6 px-5 py-6 md:px-10">
                <h2 className="text-xl font-medium">{selected.label}</h2>
                {section === "general" && (
                  <>
                    <form
                      className="flex flex-col gap-4"
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (canEdit && name.trim())
                          updateCourse.mutate({
                            id: course.id,
                            data: {
                              name: name.trim(),
                              description: description.trim() || null,
                            },
                          });
                      }}
                    >
                      <FieldGroup>
                        <Field>
                          <FieldLabel htmlFor="course-settings-name">
                            Course name
                          </FieldLabel>
                          <Input
                            id="course-settings-name"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            disabled={!canEdit || updateCourse.isPending}
                            required
                          />
                        </Field>
                        <Field>
                          <FieldLabel htmlFor="course-settings-description">
                            Description
                          </FieldLabel>
                          <Textarea
                            id="course-settings-description"
                            value={description}
                            onChange={(event) =>
                              setDescription(event.target.value)
                            }
                            disabled={!canEdit || updateCourse.isPending}
                          />
                        </Field>
                      </FieldGroup>
                      {canEdit && (
                        <Button
                          className="self-start"
                          type="submit"
                          disabled={
                            !name.trim() ||
                            updateCourse.isPending ||
                            (name === course.name &&
                              description === (course.description ?? ""))
                          }
                        >
                          {updateCourse.isPending ? "Saving…" : "Save changes"}
                        </Button>
                      )}
                      {updateCourse.isError && (
                        <p role="alert" className="text-sm text-destructive">
                          Could not save course details. Please try again.
                        </p>
                      )}
                    </form>
                    <section className="flex flex-col gap-5">
                      <h3 className="text-sm font-medium">Course actions</h3>
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm">Copy course</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Reuse this course for another class.
                          </p>
                        </div>
                        <CourseCopyDialog
                          courseId={course.id}
                          name={course.name}
                        />
                      </div>
                      {canEdit && (
                        <div className="flex items-center justify-between gap-4">
                          <div>
                            <p className="text-sm">
                              {course.isArchived
                                ? "Reopen course"
                                : "Archive course"}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {course.isArchived
                                ? "Resume teaching in this course."
                                : "Keep its work and grades for reference."}
                            </p>
                          </div>
                          <Button
                            variant="outline"
                            onClick={() => setArchiveConfirm(true)}
                          >
                            {course.isArchived ? "Reopen" : "Archive"}
                          </Button>
                        </div>
                      )}
                    </section>
                  </>
                )}
                {section === "enrollment" && (
                  <div className="flex max-w-sm flex-col gap-3">
                    <p className="text-sm text-muted-foreground">
                      Share the code with students so they can join this course.
                    </p>
                    {enrollmentControls}
                  </div>
                )}
                {section === "flows" && <FlowsTab courseId={course.id} />}
                {section === "runs" && <RunsTab courseId={course.id} />}
                {section === "capabilities" && <CapabilitiesTab />}
                {section === "artifacts" && (
                  <ArtifactsTab
                    courseId={course.id}
                    assignments={assignments}
                  />
                )}
              </div>
            </ScrollArea>
            <div className="hidden md:block" />
          </div>
        </ResponsiveDialogContent>
      </Dialog>
      <AlertDialog open={archiveConfirm} onOpenChange={setArchiveConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {course.isArchived
                ? "Reopen this course?"
                : "Archive this course?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {course.isArchived
                ? "Course work can be edited again. You can enable enrollment separately."
                : "Course work and grades will remain available. Students will no longer be able to join with the class code."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {archiveError && (
            <p role="alert" className="text-sm text-destructive">
              The course could not be updated. Please try again.
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={archivePending}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={archivePending}
              onClick={(event) => {
                event.preventDefault();
                void changeArchive();
              }}
            >
              {archivePending
                ? "Please wait…"
                : course.isArchived
                  ? "Reopen course"
                  : "Archive course"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

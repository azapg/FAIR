import {
  CloudUpload,
  CloudDownload,
  FlaskConical,
  PanelRight,
  Pencil,
  Plus,
  Share,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
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
import { cn } from "@/lib/utils";
import {
  Assignment,
  useDeleteAssignment,
  useUpdateAssignmentStatus,
} from "@/hooks/use-assignments";
import { useFlowSidebar } from "@/components/ui/sidebar";

interface AssignmentOptionsDrawerProps {
  assignment: Assignment;
  courseName?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit: () => void;
  onAddSubmission: () => void;
  showFlowsAction?: boolean;
}

function OptionRow({
  label,
  icon: Icon,
  destructive,
  onClick,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  destructive?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center justify-between px-4 py-3.5 text-left text-base transition-colors hover:bg-accent",
        destructive && "text-destructive hover:bg-destructive/10",
      )}
    >
      <span>{label}</span>
      <Icon className={cn("size-5 shrink-0", !destructive && "text-muted-foreground")} />
    </button>
  );
}

function OptionGroup({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl bg-muted/50 divide-y divide-border/60">
      {children}
    </div>
  );
}

export function AssignmentOptionsDrawer({
  assignment,
  courseName,
  open,
  onOpenChange,
  onEdit,
  onAddSubmission,
  showFlowsAction,
}: AssignmentOptionsDrawerProps) {
  const navigate = useNavigate();
  const updateAssignmentStatus = useUpdateAssignmentStatus();
  const deleteAssignment = useDeleteAssignment();
  const { toggleSidebar: toggleFlowsSidebar } = useFlowSidebar();

  const isPublished = assignment.status === "published";
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

  const close = () => onOpenChange(false);

  const handleTogglePublish = () => {
    close();
    updateAssignmentStatus.mutate({
      id: assignment.id,
      status: isPublished ? "draft" : "published",
    });
  };

  const handleShare = async () => {
    close();
    const url = window.location.href;
    const shareData = {
      title: assignment.title,
      text: courseName ? `${courseName} — ${assignment.title}` : assignment.title,
      url,
    };
    if (typeof navigator.share === "function") {
      try {
        await navigator.share(shareData);
      } catch {
        // user dismissed the share sheet
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copied to clipboard");
    } catch {
      toast.error("Failed to copy link");
    }
  };

  const handleDelete = () => {
    close();
    deleteAssignment.mutate(assignment.id, {
      onSuccess: () => {
        navigate(`/courses/${assignment.courseId}/assignments`);
      },
    });
  };

  return (
    <>
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent>
          <DrawerHeader className="sr-only">
            <DrawerTitle>Assignment options</DrawerTitle>
            <DrawerDescription>{assignment.title}</DrawerDescription>
          </DrawerHeader>
          <div className="space-y-3 overflow-y-auto px-4 pb-8">
            <OptionGroup>
              <OptionRow
                label={isPublished ? "Unpublish" : "Publish"}
                icon={isPublished ? CloudDownload : CloudUpload}
                onClick={handleTogglePublish}
              />
              <OptionRow
                label="Edit"
                icon={Pencil}
                onClick={() => {
                  close();
                  onEdit();
                }}
              />
              <OptionRow label="Share" icon={Share} onClick={handleShare} />
              {showFlowsAction && (
                <OptionRow
                  label="Flows panel"
                  icon={PanelRight}
                  onClick={() => {
                    close();
                    toggleFlowsSidebar();
                  }}
                />
              )}
            </OptionGroup>
            <OptionGroup>
              <OptionRow
                label="Delete"
                icon={Trash2}
                destructive
                onClick={() => {
                  close();
                  setIsDeleteConfirmOpen(true);
                }}
              />
            </OptionGroup>
            <div className="pt-4">
              <p className="flex items-center gap-1.5 px-1 pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/60">
                <FlaskConical className="size-3.5" />
                Developer
              </p>
              <OptionGroup>
                <OptionRow
                  label="Add submission"
                  icon={Plus}
                  onClick={() => {
                    close();
                    onAddSubmission();
                  }}
                />
              </OptionGroup>
            </div>
          </div>
        </DrawerContent>
      </Drawer>
      <DeleteAssignmentAlertDialog
        open={isDeleteConfirmOpen}
        onOpenChange={setIsDeleteConfirmOpen}
        onConfirm={handleDelete}
        isPending={deleteAssignment.isPending}
      />
    </>
  );
}

export function DeleteAssignmentAlertDialog({
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isPending?: boolean;
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete assignment?</AlertDialogTitle>
          <AlertDialogDescription>
            This will permanently delete the assignment and all of its submissions.
            This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isPending}
            className="bg-destructive text-white hover:bg-destructive/90"
          >
            {isPending ? "Deleting…" : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

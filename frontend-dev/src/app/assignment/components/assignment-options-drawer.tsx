import {
  CloudDownload,
  CloudUpload,
  FlaskConical,
  PanelRight,
  Pencil,
  Plus,
  Share,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { useState, type ReactElement, type ReactNode } from "react";

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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  Assignment,
  useDeleteAssignment,
  useUpdateAssignmentStatus,
} from "@/hooks/use-assignments";
import { useFlowSidebar } from "@/components/ui/sidebar";

export interface AssignmentOptionsProps {
  assignment: Assignment;
  courseName?: string;
  onEdit: () => void;
  onAddSubmission: () => void;
  showFlowsAction?: boolean;
}

interface AssignmentOptionsDrawerProps extends AssignmentOptionsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface AssignmentOption {
  label: string;
  icon: LucideIcon;
  destructive?: boolean;
  onClick: () => void;
}

interface AssignmentOptionGroups {
  primary: AssignmentOption[];
  destructive: AssignmentOption[];
  developer: AssignmentOption[];
}

function OptionRow({
  label,
  icon: Icon,
  destructive,
  onClick,
}: AssignmentOption) {
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

function OptionGroup({ children }: { children: ReactNode }) {
  return (
    <div className="divide-y divide-border/60 overflow-hidden rounded-xl bg-muted/50">
      {children}
    </div>
  );
}

function useAssignmentOptionsActions({
  assignment,
  courseName,
}: Pick<AssignmentOptionsProps, "assignment" | "courseName">) {
  const navigate = useNavigate();
  const updateAssignmentStatus = useUpdateAssignmentStatus();
  const deleteAssignment = useDeleteAssignment();
  const { toggleSidebar: toggleFlowsSidebar } = useFlowSidebar();

  const isPublished = assignment.status === "published";
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);

  const handleTogglePublish = () => {
    updateAssignmentStatus.mutate({
      id: assignment.id,
      status: isPublished ? "draft" : "published",
    });
  };

  const handleShare = async () => {
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
    deleteAssignment.mutate(assignment.id, {
      onSuccess: () => {
        navigate(`/courses/${assignment.courseId}/assignments`);
      },
    });
  };

  return {
    isPublished,
    handleTogglePublish,
    handleShare,
    handleDelete,
    deleteAssignment,
    isDeleteConfirmOpen,
    setIsDeleteConfirmOpen,
    toggleFlowsSidebar,
  };
}

function getOptionGroups(
  props: AssignmentOptionsProps & {
    close: () => void;
    actions: ReturnType<typeof useAssignmentOptionsActions>;
  },
): AssignmentOptionGroups {
  const { assignment, onEdit, onAddSubmission, showFlowsAction, close, actions } = props;

  return {
    primary: [
      {
        label: actions.isPublished ? "Unpublish" : "Publish",
        icon: actions.isPublished ? CloudDownload : CloudUpload,
        onClick: () => {
          close();
          actions.handleTogglePublish();
        },
      },
      {
        label: "Edit",
        icon: Pencil,
        onClick: () => {
          close();
          onEdit();
        },
      },
      {
        label: "Share",
        icon: Share,
        onClick: () => {
          close();
          void actions.handleShare();
        },
      },
      ...(showFlowsAction
        ? [{
            label: "Flows panel",
            icon: PanelRight,
            onClick: () => {
              close();
              actions.toggleFlowsSidebar();
            },
          }]
        : []),
    ],
    destructive: [
      {
        label: "Delete",
        icon: Trash2,
        destructive: true,
        onClick: () => {
          close();
          actions.setIsDeleteConfirmOpen(true);
        },
      },
    ],
    developer: [
      {
        label: "Add submission",
        icon: Plus,
        onClick: () => {
          close();
          onAddSubmission();
        },
      },
    ],
  };
}

function OptionDropdownItem({
  label,
  icon: Icon,
  destructive,
  onClick,
}: AssignmentOption) {
  return (
    <DropdownMenuItem variant={destructive ? "destructive" : "default"} onSelect={onClick}>
      <Icon />
      {label}
    </DropdownMenuItem>
  );
}

export function AssignmentOptionsDropdown({
  trigger,
  ...props
}: AssignmentOptionsProps & { trigger: ReactElement }) {
  const actions = useAssignmentOptionsActions(props);
  const groups = getOptionGroups({ ...props, close: () => {}, actions });

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          {groups.primary.map((option) => (
            <OptionDropdownItem key={option.label} {...option} />
          ))}
          <DropdownMenuSeparator />
          {groups.destructive.map((option) => (
            <OptionDropdownItem key={option.label} {...option} />
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuLabel>Developer</DropdownMenuLabel>
          {groups.developer.map((option) => (
            <OptionDropdownItem key={option.label} {...option} />
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <DeleteAssignmentAlertDialog
        open={actions.isDeleteConfirmOpen}
        onOpenChange={actions.setIsDeleteConfirmOpen}
        onConfirm={actions.handleDelete}
        isPending={actions.deleteAssignment.isPending}
      />
    </>
  );
}

export function AssignmentOptionsDrawer({
  open,
  onOpenChange,
  ...props
}: AssignmentOptionsDrawerProps) {
  const actions = useAssignmentOptionsActions(props);
  const groups = getOptionGroups({ ...props, close: () => onOpenChange(false), actions });

  return (
    <>
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent>
          <DrawerHeader className="sr-only">
            <DrawerTitle>Assignment options</DrawerTitle>
            <DrawerDescription>{props.assignment.title}</DrawerDescription>
          </DrawerHeader>
          <div className="space-y-3 overflow-y-auto px-4 pb-8">
            <OptionGroup>
              {groups.primary.map((option) => (
                <OptionRow key={option.label} {...option} />
              ))}
            </OptionGroup>
            <OptionGroup>
              {groups.destructive.map((option) => (
                <OptionRow key={option.label} {...option} />
              ))}
            </OptionGroup>
            <div className="pt-4">
              <p className="flex items-center gap-1.5 px-1 pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/60">
                <FlaskConical className="size-3.5" />
                Developer
              </p>
              <OptionGroup>
                {groups.developer.map((option) => (
                  <OptionRow key={option.label} {...option} />
                ))}
              </OptionGroup>
            </div>
          </div>
        </DrawerContent>
      </Drawer>
      <DeleteAssignmentAlertDialog
        open={actions.isDeleteConfirmOpen}
        onOpenChange={actions.setIsDeleteConfirmOpen}
        onConfirm={actions.handleDelete}
        isPending={actions.deleteAssignment.isPending}
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

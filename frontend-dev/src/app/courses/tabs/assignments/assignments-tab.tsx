import {useState, useEffect} from "react";
import {AssignmentsTable} from "@/app/courses/tabs/assignments/assignments-table";
import {useAssignmentColumns} from "@/app/courses/tabs/assignments/assignments";
import {CreateAssignmentDialog} from "@/app/courses/tabs/assignments/create-assignment-dialog";
import {Assignment, useDeleteAssignment} from "@/hooks/use-assignments";
import {useTranslation} from "react-i18next";
import {EditAssignmentDialog} from "@/app/courses/tabs/assignments/edit-assignment-dialog";
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

// TODO: Let's just use react-query here directly to manage assignments state
export default function AssignmentsTab({
  assignments: initialAssignments = [],
  courseId,
  canManageAssignments = true,
}: {
  assignments?: Assignment[];
  courseId?: string;
  canManageAssignments?: boolean;
}) {
  const [assignments, setAssignments] = useState<Assignment[]>(() => initialAssignments);
  const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Assignment | null>(null);
  const {t} = useTranslation();
  const deleteAssignment = useDeleteAssignment();
  const columns = useAssignmentColumns({
    canManage: canManageAssignments,
    onEdit: canManageAssignments ? (assignment) => {
      setEditingAssignment(assignment);
      setIsEditOpen(true);
    } : undefined,
    onDelete: canManageAssignments ? (assignment) => {
      setDeleteTarget(assignment);
    } : undefined,
  });

  useEffect(() => {
    setAssignments(initialAssignments);
  }, [initialAssignments]);

  const handleAssignmentCreated = (newAssignment: Assignment) => {
    setAssignments(prev => [...prev, newAssignment]);
  };

  const handleAssignmentUpdated = (updated: Assignment) => {
    setAssignments(prev => prev.map(item => item.id === updated.id ? updated : item));
  };

  const handleEditOpenChange = (open: boolean) => {
    setIsEditOpen(open);
    if (!open) {
      setEditingAssignment(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    await deleteAssignment.mutateAsync(deleteTarget.id);
    setAssignments(prev => prev.filter(item => item.id !== deleteTarget.id));
    setDeleteTarget(null);
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl">{t("assignments.title")}</h2>
        {canManageAssignments && (
          <CreateAssignmentDialog
            courseId={courseId}
            onAssignmentCreated={handleAssignmentCreated}
            open={isCreateOpen}
            onOpenChange={setIsCreateOpen}
          />
        )}
      </div>

      <AssignmentsTable
        columns={columns}
        data={assignments}
        onCreateAssignment={
          canManageAssignments ? () => setIsCreateOpen(true) : undefined
        }
      />
      {canManageAssignments && (
        <EditAssignmentDialog
          assignment={editingAssignment}
          open={isEditOpen}
          onOpenChange={handleEditOpenChange}
          onAssignmentUpdated={handleAssignmentUpdated}
        />
      )}
      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("assignments.deleteConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("assignments.deleteConfirmDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>
              {t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

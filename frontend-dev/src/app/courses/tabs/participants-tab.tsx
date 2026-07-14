import { ColumnDef } from "@tanstack/react-table";
import { Ellipsis } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DataTable, DataTableContent, DataTableEmpty } from "@/components/data-table";
import {
  EnrollmentSummary,
  useCourseEnrollments,
  useRemoveEnrollment,
  useUpdateEnrollmentRole,
} from "@/hooks/use-courses";

type Instructor = {
  id: string;
  name: string;
  email: string;
  role: string;
};

export function ParticipantsTab({
  courseId,
  instructor,
  canManageRoles,
}: {
  courseId: string;
  instructor?: Instructor;
  canManageRoles: boolean;
}) {
  const { t } = useTranslation();
  const { data: memberships = [], isLoading } = useCourseEnrollments(courseId);
  const removeEnrollment = useRemoveEnrollment(courseId);
  const updateRole = useUpdateEnrollmentRole(courseId);
  const assistants = memberships.filter((membership) => membership.role === 'assistant');
  const instructors = useMemo(
    () => [
      ...(instructor ? [instructor] : []),
      ...assistants.map((membership) => ({
        id: membership.userId,
        name: membership.userName ?? 'Assistant',
        email: membership.userEmail ?? '',
        role: 'assistant',
      })),
    ],
    [instructor, assistants],
  );
  const students = memberships.filter((membership) => membership.role === 'student');

  const instructorColumns = useMemo<ColumnDef<Instructor>[]>(
    () => [
      {
        accessorKey: "name",
        header: t("courses.instructor"),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback>
                {row.original.name?.[0]?.toUpperCase() ?? "I"}
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="font-medium">{row.original.name}</span>
              <span className="text-xs text-muted-foreground capitalize">{row.original.role}</span>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "email",
        header: t("auth.email"),
        cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.email}</span>,
      },
      {
        id: "description",
        header: t("courses.description"),
        cell: () => <span className="text-sm text-muted-foreground">{t("participants.instructorRole")}</span>,
      },
      {
        id: "actions",
        header: () => <div className="w-12 text-right">{t("actions.courseActions")}</div>,
        cell: () => (
          <div className="text-right">
            <DropdownMenu>
              <DropdownMenuTrigger className="ml-auto flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
                <Ellipsis className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled>View profile</DropdownMenuItem>
                <DropdownMenuItem disabled>{t("common.edit")}</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [t],
  );

  const studentColumns = useMemo<ColumnDef<EnrollmentSummary>[]>(
    () => [
      {
        accessorKey: "userName",
        header: t("participants.students"),
      },
      {
        accessorKey: "userEmail",
        header: t("auth.email"),
      },
      {
        id: "description",
        header: t("courses.description"),
        cell: ({ row }) => <span className="capitalize">{row.original.role}</span>,
      },
      {
        id: "actions",
        header: () => <div className="w-12 text-right">{t("actions.courseActions")}</div>,
        cell: ({ row }) => (
          <div className="text-right">
            <DropdownMenu>
              <DropdownMenuTrigger className="ml-auto flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
                <Ellipsis className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {canManageRoles && (
                  <DropdownMenuItem
                    onClick={() => updateRole.mutate({ id: row.original.id, role: 'assistant' })}
                  >
                    Make assistant
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => removeEnrollment.mutate(row.original.id)}
                >
                  Remove from course
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [canManageRoles, removeEnrollment, t, updateRole],
  );

  return (
    <div className="space-y-4">
      <h2 className="mb-3 text-xl font-semibold">{t("participants.instructors")}</h2>
      <DataTable data={instructors} columns={instructorColumns}>
        <DataTableContent>
          <DataTableEmpty>{t("participants.noInstructor")}</DataTableEmpty>
        </DataTableContent>
      </DataTable>

      <h2 className="mb-2 text-xl font-semibold">{t("participants.students")}</h2>
      <DataTable data={students} columns={studentColumns}>
        <DataTableContent>
          <DataTableEmpty>
            {isLoading ? t("common.loading") : t("participants.noStudents")}
          </DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

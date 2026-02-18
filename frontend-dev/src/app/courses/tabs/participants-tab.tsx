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

type Instructor = {
  id: string;
  name: string;
  email: string;
  role: string;
};

type Student = {
  id: string;
  name: string;
  email: string;
};

export function ParticipantsTab({ instructor }: { instructor?: Instructor }) {
  const { t } = useTranslation();
  const instructors = useMemo(() => (instructor ? [instructor] : []), [instructor]);

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

  const studentColumns = useMemo<ColumnDef<Student>[]>(
    () => [
      {
        accessorKey: "name",
        header: t("participants.students"),
      },
      {
        accessorKey: "email",
        header: t("auth.email"),
      },
      {
        id: "description",
        header: t("courses.description"),
      },
      {
        id: "actions",
        header: () => <div className="w-12 text-right">{t("actions.courseActions")}</div>,
      },
    ],
    [t],
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
      <DataTable data={[]} columns={studentColumns}>
        <DataTableContent>
          <DataTableEmpty>{t("participants.noStudents")}</DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

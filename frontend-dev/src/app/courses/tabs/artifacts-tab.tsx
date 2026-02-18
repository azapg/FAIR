import { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Assignment } from "@/hooks/use-assignments";
import { Artifact, useArtifacts, useDeleteArtifact } from "@/hooks/use-artifacts";
import { Button } from "@/components/ui/button";
import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table";

export function ArtifactsTab({
  courseId,
  assignments,
}: {
  courseId?: string;
  assignments: Assignment[];
}) {
  const { t } = useTranslation();
  const { data: artifacts, isLoading, isError, refetch } = useArtifacts(
    courseId ? { courseId } : undefined,
    Boolean(courseId),
  );
  const deleteArtifact = useDeleteArtifact();

  const assignmentNames = useMemo(() => {
    const map = new Map<string, string>();
    assignments?.forEach((a) => map.set(a.id, a.title));
    return map;
  }, [assignments]);

  const columns = useMemo<ColumnDef<Artifact>[]>(
    () => [
      {
        accessorKey: "title",
        header: t("assignments.titleLabel"),
        cell: ({ row }) => <span className="font-medium">{row.original.title}</span>,
      },
      {
        id: "assignment",
        header: t("artifacts.assignment"),
        cell: ({ row }) =>
          row.original.assignmentId
            ? assignmentNames.get(row.original.assignmentId) ?? row.original.assignmentId
            : t("assignments.na"),
      },
      {
        accessorKey: "status",
        header: t("artifacts.status"),
        cell: ({ row }) => <span className="capitalize">{row.original.status}</span>,
      },
      {
        accessorKey: "accessLevel",
        header: t("artifacts.access"),
        cell: ({ row }) => <span className="capitalize">{row.original.accessLevel}</span>,
      },
      {
        accessorKey: "updatedAt",
        header: t("artifacts.updated"),
        cell: ({ row }) =>
          row.original.updatedAt ? new Date(row.original.updatedAt).toLocaleString() : "—",
      },
      {
        id: "actions",
        header: () => <div className="text-right">{t("actions.courseActions")}</div>,
        cell: ({ row }) => (
          <div className="text-right">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void handleDelete(row.original.id)}
            >
              {t("common.delete")}
            </Button>
          </div>
        ),
      },
    ],
    [assignmentNames, t],
  );

  const archivedColumns = useMemo<ColumnDef<Artifact>[]>(
    () => [
      {
        accessorKey: "title",
        header: t("assignments.titleLabel"),
        cell: ({ row }) => <span className="font-medium">{row.original.title}</span>,
      },
      {
        id: "assignment",
        header: t("artifacts.assignment"),
        cell: ({ row }) =>
          row.original.assignmentId
            ? assignmentNames.get(row.original.assignmentId) ?? row.original.assignmentId
            : t("assignments.na"),
      },
      {
        accessorKey: "status",
        header: t("artifacts.status"),
        cell: ({ row }) => <span className="capitalize">{row.original.status}</span>,
      },
      {
        accessorKey: "updatedAt",
        header: t("artifacts.updated"),
        cell: ({ row }) =>
          row.original.updatedAt ? new Date(row.original.updatedAt).toLocaleString() : "—",
      },
    ],
    [assignmentNames, t],
  );

  if (!courseId) {
    return <div className="text-sm text-muted-foreground">{t("artifacts.noCourse")}</div>;
  }

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError) {
    return <div>{t("artifacts.errorLoading")}</div>;
  }

  if (!artifacts || artifacts.length === 0) {
    return <div className="text-sm text-muted-foreground">{t("artifacts.empty")}</div>;
  }

  const activeArtifacts = artifacts.filter((artifact) => artifact.status !== "archived");
  const archivedArtifacts = artifacts.filter((artifact) => artifact.status === "archived");

  async function handleDelete(artifactId: string) {
    await deleteArtifact.mutateAsync(artifactId);
    await refetch();
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("artifacts.title")}</h3>

      <DataTable data={activeArtifacts} columns={columns} filterKey="title">
        <div className="pb-3">
          <DataTableSearch />
        </div>
        <DataTableContent>
          <DataTableEmpty>{t("artifacts.empty")}</DataTableEmpty>
        </DataTableContent>
      </DataTable>

      {archivedArtifacts.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-lg font-semibold">{t("artifacts.archivedTitle")}</h4>
          <DataTable data={archivedArtifacts} columns={archivedColumns}>
            <DataTableContent>
              <DataTableEmpty>{t("artifacts.empty")}</DataTableEmpty>
            </DataTableContent>
          </DataTable>
        </div>
      )}
    </div>
  );
}

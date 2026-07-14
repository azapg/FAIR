import { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table";
import { Flow, latestPublishedVersion, useFlows } from "@/hooks/use-flows";

export function FlowsTab({ courseId }: { courseId?: string }) {
  const flowsQuery = useFlows(courseId, Boolean(courseId));
  const columns = useMemo<ColumnDef<Flow>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Flow",
        cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      },
      {
        accessorKey: "description",
        header: "Description",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.description || "—"}
          </span>
        ),
      },
      {
        id: "publishedVersion",
        header: "Published version",
        cell: ({ row }) => latestPublishedVersion(row.original)?.ordinal ?? "—",
      },
      {
        id: "nodes",
        header: "Ordered nodes",
        cell: ({ row }) =>
          latestPublishedVersion(row.original)?.definition.nodes.length ?? "—",
      },
    ],
    [],
  );

  if (!courseId) {
    return <div className="text-sm text-muted-foreground">No course selected</div>;
  }
  if (flowsQuery.isLoading) return <div>Loading…</div>;
  if (flowsQuery.isError) return <div>Flows could not be loaded.</div>;

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">Flows</h3>
      <DataTable data={flowsQuery.data ?? []} columns={columns} filterKey="name">
        <div className="pb-3">
          <DataTableSearch />
        </div>
        <DataTableContent>
          <DataTableEmpty>No Flows have been created for this course.</DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

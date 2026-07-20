import { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table";
import {
  CapabilityDefinition,
  useCapabilities,
} from "@/hooks/use-extensions";

export function CapabilitiesTab() {
  const capabilities = useCapabilities();
  const columns = useMemo<ColumnDef<CapabilityDefinition>[]>(
    () => [
      {
        accessorKey: "capabilityId",
        header: "Capability",
        cell: ({ row }) => (
          <span className="font-medium">{row.original.capabilityId}</span>
        ),
      },
      { accessorKey: "surface", header: "Surface" },
      {
        id: "contract",
        header: "Contract",
        cell: ({ row }) => row.original.contract ?? "—",
      },
      { accessorKey: "version", header: "Version" },
      {
        id: "effects",
        header: "Declared effects",
        cell: ({ row }) => row.original.declaredEffects.join(", ") || "None",
      },
      {
        id: "features",
        header: "Runtime features",
        cell: ({ row }) =>
          [
            row.original.supportsStreaming && "streaming",
            row.original.supportsCancellation && "cancellation",
            row.original.supportsResume && "resume",
          ]
            .filter(Boolean)
            .join(", ") || "basic",
      },
    ],
    [],
  );

  if (capabilities.isLoading) return <div>Loading…</div>;
  if (capabilities.isError) return <div>Capabilities could not be loaded.</div>;

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">Extension capabilities</h3>
      <DataTable
        data={capabilities.data ?? []}
        columns={columns}
        filterKey="capabilityId"
      >
        <div className="pb-3">
          <DataTableSearch />
        </div>
        <DataTableContent>
          <DataTableEmpty>No enabled Extension exposes a capability.</DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

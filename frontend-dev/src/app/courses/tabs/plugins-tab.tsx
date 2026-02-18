import { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table";
import { RuntimePluginRead, usePlugins } from "@/hooks/use-plugins";

export function PluginsTab() {
  const { t } = useTranslation();
  const { data: plugins, isLoading, isError } = usePlugins();

  const columns = useMemo<ColumnDef<RuntimePluginRead>[]>(
    () => [
      {
        accessorKey: "name",
        header: t("assignments.titleLabel"),
        cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      },
      {
        accessorKey: "type",
        header: t("plugins.type"),
        cell: ({ row }) => <span className="capitalize">{row.original.type}</span>,
      },
      {
        accessorKey: "version",
        header: t("plugins.version"),
      },
      {
        accessorKey: "author",
        header: t("plugins.author"),
        cell: ({ row }) => row.original.author || "—",
      },
      {
        accessorKey: "source",
        header: t("plugins.source"),
        cell: ({ row }) => <span className="block max-w-[240px] truncate">{row.original.source}</span>,
      },
    ],
    [t],
  );

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (isError) {
    return <div>{t("plugins.errorLoadingPlugins")}</div>;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("tabs.plugins")}</h3>
      <DataTable data={plugins ?? []} columns={columns} filterKey="name">
        <div className="pb-3">
          <DataTableSearch />
        </div>
        <DataTableContent>
          <DataTableEmpty>{t("plugins.empty")}</DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

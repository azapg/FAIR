import { ColumnDef } from "@tanstack/react-table";
import { Ellipsis, Pencil, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { BreadcrumbNav } from "@/components/breadcrumb-nav";
import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Rubric, useDeleteRubric, useRubrics } from "@/hooks/use-rubrics";

import { RubricFormDialog } from "./components/rubric-form-dialog";
import { RubricMatrixView } from "./components/rubric-matrix-view";
import { normalizeContent } from "./utils";

export default function RubricsPage() {
  const { t } = useTranslation();
  const { data: rubrics = [], isLoading } = useRubrics();
  const deleteRubric = useDeleteRubric();

  const [selectedRubric, setSelectedRubric] = useState<Rubric | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editRubric, setEditRubric] = useState<Rubric | null>(null);

  const columns = useMemo<ColumnDef<Rubric>[]>(
    () => [
      {
        accessorKey: "name",
        header: t("rubrics.columns.name"),
      },
      {
        id: "criteria",
        header: t("rubrics.columns.criteria"),
        cell: ({ row }) => row.original.content.criteria.length,
      },
      {
        id: "levels",
        header: t("rubrics.columns.levels"),
        cell: ({ row }) => row.original.content.levels.length,
      },
      {
        accessorKey: "createdAt",
        header: t("rubrics.columns.created"),
        cell: ({ row }) => new Date(row.original.createdAt).toLocaleDateString(),
      },
      {
        id: "actions",
        cell: ({ row }) => (
          <div className="text-right" onClick={(event) => event.stopPropagation()}>
            <DropdownMenu>
              <DropdownMenuTrigger className="ml-auto flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted">
                <Ellipsis className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => {
                    setEditRubric(row.original);
                  }}
                >
                  <Pencil className="mr-2 h-4 w-4" />
                  {t("common.edit")}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    deleteRubric.mutate(row.original.id);
                  }}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("common.delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [deleteRubric, t],
  );

  return (
    <main className="flex flex-col justify-center">
      <div className="px-5 py-2">
        <BreadcrumbNav
          segments={[
            {
              label: t("rubrics.title"),
              slug: "rubrics",
            },
          ]}
        />
      </div>

      <div className="flex items-center justify-between px-6 pt-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t("rubrics.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("rubrics.subtitle")}</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("rubrics.createAction")}
        </Button>
      </div>

      <div className="px-6 py-4">
        <DataTable
          data={rubrics}
          columns={columns}
          filterKey="name"
          onRowClick={(row) => setSelectedRubric(row)}
        >
          <div className="pb-3">
            <DataTableSearch />
          </div>
          <DataTableContent className="rounded-lg border">
            <DataTableEmpty>{isLoading ? t("common.loading") : t("rubrics.empty")}</DataTableEmpty>
          </DataTableContent>
        </DataTable>
      </div>

      <RubricFormDialog open={showCreate} onOpenChange={setShowCreate} />
      <RubricFormDialog
        open={!!editRubric}
        onOpenChange={(open) => {
          if (!open) setEditRubric(null);
        }}
        rubric={editRubric}
      />

      <Dialog
        open={!!selectedRubric}
        onOpenChange={(open) => {
          if (!open) setSelectedRubric(null);
        }}
      >
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-[95vw]">
          <DialogHeader>
            <DialogTitle>{selectedRubric?.name}</DialogTitle>
            <DialogDescription>{t("rubrics.detailDescription")}</DialogDescription>
          </DialogHeader>

          {selectedRubric ? (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">{t("rubrics.levelMeaningHint")}</p>
              <RubricMatrixView content={normalizeContent(selectedRubric.content)} />
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </main>
  );
}

import { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ExtensionPluginRead } from "@/hooks/use-plugins";
import { workflowPluginsFromSteps, WorkflowStep } from "@/store/workflows-store";
import {
  DataTable,
  DataTableContent,
  DataTableEmpty,
  DataTableSearch,
} from "@/components/data-table";

type WorkflowRow = {
  id: string;
  name: string;
  description?: string | null;
  createdAt: string;
  updatedAt?: string | null;
  plugins?: Record<string, ExtensionPluginRead>;
  steps?: WorkflowStep[];
};

export function WorkflowsTab({ courseId }: { courseId?: string }) {
  const { t } = useTranslation();

  const workflowsQuery = useQuery<WorkflowRow[]>({
    enabled: Boolean(courseId),
    queryKey: ["workflows", "course", courseId],
    queryFn: async () => {
      if (!courseId) return [];
      const res = await api.get("/workflows", { params: { course_id: courseId } });
      return (res.data as WorkflowRow[]).map((workflow) => ({
        ...workflow,
        plugins: workflowPluginsFromSteps(workflow.steps),
      }));
    },
  });

  const deleteWorkflow = useMutation({
    mutationFn: async (workflowId: string) => api.delete(`/workflows/${workflowId}`),
    onSuccess: () => workflowsQuery.refetch(),
  });

  const columns = useMemo<ColumnDef<WorkflowRow>[]>(
    () => [
      {
        accessorKey: "name",
        header: t("assignments.titleLabel"),
        cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      },
      {
        accessorKey: "description",
        header: t("workflow.workflowDetails"),
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.description || t("assignments.na")}
          </span>
        ),
      },
      {
        id: "transcriber",
        header: t("plugins.transcriber"),
        cell: ({ row }) => row.original.plugins?.transcriber?.name ?? t("assignments.na"),
      },
      {
        id: "grader",
        header: t("plugins.grader"),
        cell: ({ row }) => row.original.plugins?.grader?.name ?? t("assignments.na"),
      },
      {
        id: "reviewer",
        header: t("plugins.reviewer"),
        cell: ({ row }) => row.original.plugins?.reviewer?.name ?? t("assignments.na"),
      },
      {
        id: "actions",
        header: () => <div className="text-right">{t("actions.courseActions")}</div>,
        cell: ({ row }) => (
          <div className="text-right">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteWorkflow.mutate(row.original.id)}
            >
              {t("common.delete")}
            </Button>
          </div>
        ),
      },
    ],
    [deleteWorkflow, t],
  );

  if (!courseId) {
    return <div className="text-sm text-muted-foreground">{t("workflow.noCourseSelected")}</div>;
  }

  if (workflowsQuery.isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (workflowsQuery.isError) {
    return <div>{t("workflow.errorLoading")}</div>;
  }

  const workflows = workflowsQuery.data ?? [];

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("tabs.workflows")}</h3>
      <DataTable data={workflows} columns={columns} filterKey="name">
        <div className="pb-3">
          <DataTableSearch />
        </div>
        <DataTableContent>
          <DataTableEmpty>{t("workflow.noWorkflowsMessage")}</DataTableEmpty>
        </DataTableContent>
      </DataTable>
    </div>
  );
}

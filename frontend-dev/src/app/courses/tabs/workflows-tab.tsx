import {useTranslation} from "react-i18next";
import {useMutation, useQuery} from "@tanstack/react-query";
import api from "@/lib/api";
import {Button} from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import {RuntimePluginRead} from "@/hooks/use-plugins";

type WorkflowRow = {
  id: string;
  name: string;
  description?: string | null;
  createdAt: string;
  updatedAt?: string | null;
  plugins?: Record<string, RuntimePluginRead>;
};

export function WorkflowsTab({courseId}: { courseId?: string }) {
  const {t} = useTranslation();

  const workflowsQuery = useQuery<WorkflowRow[]>({
    enabled: Boolean(courseId),
    queryKey: ["workflows", "course", courseId],
    queryFn: async () => {
      if (!courseId) return [];
      const res = await api.get("/workflows", {params: {course_id: courseId}});
      return res.data;
    },
  });

  const deleteWorkflow = useMutation({
    mutationFn: async (workflowId: string) => api.delete(`/workflows/${workflowId}`),
    onSuccess: () => workflowsQuery.refetch(),
  });

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

  if (workflows.length === 0) {
    return <div className="text-sm text-muted-foreground">{t("workflow.noWorkflowsMessage")}</div>;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xl font-semibold">{t("tabs.workflows")}</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("assignments.titleLabel")}</TableHead>
            <TableHead>{t("workflow.workflowDetails")}</TableHead>
            <TableHead>{t("plugins.transcriber")}</TableHead>
            <TableHead>{t("plugins.grader")}</TableHead>
            <TableHead>{t("plugins.validator")}</TableHead>
            <TableHead className="text-right">{t("actions.courseActions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {workflows.map((wf) => (
            <TableRow key={wf.id}>
              <TableCell className="font-medium">{wf.name}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {wf.description || t("assignments.na")}
              </TableCell>
              <TableCell className="text-sm">{wf.plugins?.transcriber?.name ?? t("assignments.na")}</TableCell>
              <TableCell className="text-sm">{wf.plugins?.grader?.name ?? t("assignments.na")}</TableCell>
              <TableCell className="text-sm">{wf.plugins?.validator?.name ?? t("assignments.na")}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteWorkflow.mutate(wf.id)}
                >
                  {t("common.delete")}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

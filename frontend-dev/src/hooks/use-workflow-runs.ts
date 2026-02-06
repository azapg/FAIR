import { useQuery } from "@tanstack/react-query";

import api from "@/lib/api";
import { WorkflowRun } from "@/store/workflows-store";

type WorkflowRunFilters = {
  courseId?: string;
  assignmentId?: string;
  workflowId?: string;
  enabled?: boolean;
};

const keys = {
  runs: (courseId?: string | null, assignmentId?: string | null, workflowId?: string | null) =>
    ["workflow-runs", courseId || "all", assignmentId || "all", workflowId || "all"] as const,
};

export function useWorkflowRuns(filters: WorkflowRunFilters) {
  const { courseId, assignmentId, workflowId, enabled = true } = filters;
  const isEnabled = enabled && !!(courseId || assignmentId || workflowId);

  return useQuery<WorkflowRun[]>({
    queryKey: keys.runs(courseId ?? null, assignmentId ?? null, workflowId ?? null),
    enabled: isEnabled,
    queryFn: async () => {
      const response = await api.get("/workflow-runs", {
        params: {
          course_id: courseId,
          assignment_id: assignmentId,
          workflow_id: workflowId,
        },
      });
      return response.data as WorkflowRun[];
    },
  });
}

export const workflowRunKeys = keys;

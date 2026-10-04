import { useQuery } from "@tanstack/react-query";

import api from "@/lib/api";

export type ExecutionStatus =
  | "queued"
  | "running"
  | "waiting"
  | "completed"
  | "failed"
  | "cancelled"
  | "expired";

export type Execution = {
  id: string;
  threadId?: string | null;
  turnId?: string | null;
  courseId?: string | null;
  assignmentId?: string | null;
  submissionIds: string[];
  parentExecutionId?: string | null;
  rootExecutionId: string;
  retryOfExecutionId?: string | null;
  attempt: number;
  kind: string;
  capabilityId?: string | null;
  capabilityVersion?: string | null;
  flowVersionId?: string | null;
  initiatedByUserId?: string | null;
  extensionInstallationId?: string | null;
  status: ExecutionStatus;
  waitingReason?: string | null;
  createdAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  errorCode?: string | null;
  errorSummary?: string | null;
  outputSummary?: Record<string, unknown> | null;
  snapshot?: Record<string, unknown> | null;
};

type ExecutionFilters = {
  courseId?: string;
  assignmentId?: string;
  submissionId?: string;
  flowVersionId?: string;
  status?: ExecutionStatus;
  kind?: string;
  enabled?: boolean;
};

export const executionKeys = {
  all: ["executions"] as const,
  lists: () => [...executionKeys.all, "list"] as const,
  list: (filters: Omit<ExecutionFilters, "enabled">) =>
    [...executionKeys.lists(), filters] as const,
};

export function useExecutions(filters: ExecutionFilters) {
  const { enabled = true, ...query } = filters;
  return useQuery<Execution[]>({
    queryKey: executionKeys.list(query),
    enabled,
    queryFn: async () => {
      const response = await api.get("/v1/executions", {
        params: {
          course_id: query.courseId,
          assignment_id: query.assignmentId,
          submission_id: query.submissionId,
          flow_version_id: query.flowVersionId,
          status: query.status,
          kind: query.kind,
        },
      });
      return response.data as Execution[];
    },
  });
}

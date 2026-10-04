import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export type FlowNode = {
  id: string;
  capabilityDefinitionId: string;
  input: Record<string, unknown>;
  config: Record<string, unknown>;
  timeoutSeconds: number;
  maxAttempts: number;
  onFailure: "fail" | "continue";
};

export type FlowVersion = {
  id: string;
  flowId: string;
  ordinal: number;
  state: "draft" | "published" | "archived";
  definition: { mode: "ordered"; nodes: FlowNode[] };
  definitionHash: string;
};

export type Flow = {
  id: string;
  ownerUserId: string;
  courseId?: string | null;
  name: string;
  description?: string | null;
  versions: FlowVersion[];
};

const flowKeys = {
  all: ["flows"] as const,
  list: (courseId?: string) => ["flows", { courseId }] as const,
};

export function useFlows(courseId?: string, enabled = true) {
  return useQuery({
    queryKey: flowKeys.list(courseId),
    enabled,
    queryFn: async (): Promise<Flow[]> => {
      const response = await api.get("/v1/flows");
      const flows = response.data as Flow[];
      return courseId ? flows.filter((flow) => flow.courseId === courseId) : flows;
    },
  });
}

export function useCreateFlow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      description?: string;
      courseId?: string;
    }): Promise<Flow> => {
      const response = await api.post("/v1/flows", payload);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: flowKeys.all }),
  });
}

export function useStartFlow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      flowId,
      flowVersionId,
      assignmentId,
      submissionIds,
    }: {
      flowId: string;
      flowVersionId: string;
      assignmentId?: string;
      submissionIds?: string[];
    }) => {
      const response = await api.post(`/v1/flows/${flowId}/executions`, {
        flowVersionId,
        assignmentId,
        submissionIds: submissionIds ?? [],
      });
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["executions"] }),
  });
}

export function latestPublishedVersion(flow?: Flow): FlowVersion | undefined {
  return flow?.versions
    .filter((version) => version.state === "published")
    .sort((left, right) => right.ordinal - left.ordinal)[0];
}

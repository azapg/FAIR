import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import api from "@/lib/api";
import { useWorkflowStore } from "@/store/workflows-store";
import type { Workflow } from "@/store/workflows-store";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";

const keys = {
  workflows: (courseId: string) => ["workflows", courseId] as const,
};

export function useWorkflows() {
  const drafts = useWorkflowStore((s) => s.drafts);
  const saveDraft = useWorkflowStore((s) => s.saveDraft);
  const courseId = useWorkflowStore((s) => s.activeCourseId);
  const setActiveWorkflowId = useWorkflowStore((s) => s.setActiveWorkflowId);
  const { user } = useAuth();

  const query = useQuery<Workflow[]>({
    enabled: !!courseId,
    queryKey: courseId ? keys.workflows(courseId) : ["workflows", "no-course"],
    queryFn: async () => {
      if (!courseId) return [];
      const res = await api.get("/workflows", { params: { course_id: courseId } });
      return res.data as Workflow[];
    },
  });

  useEffect(() => {
    if (!courseId) return;
    const workflows = query.data;
    if (!workflows || workflows.length === 0) return;

    const state = useWorkflowStore.getState();
    const currentActive = state.activeWorkflowId;
    const lastActiveForCourse = state.coursesActiveWorkflows[courseId];

    const isCurrentValid = !!(
      currentActive && workflows.some((w: Workflow) => w.id === currentActive)
    );
    const isLastValid = !!(
      lastActiveForCourse && workflows.some((w: Workflow) => w.id === lastActiveForCourse)
    );

    const nextActive =
      (isCurrentValid
        ? currentActive
        : isLastValid
          ? lastActiveForCourse
          : workflows[0]?.id) || undefined;

    if (nextActive && nextActive !== currentActive) {
      setActiveWorkflowId(nextActive);
    }

    const wf = nextActive ? workflows.find((w: Workflow) => w.id === nextActive) : undefined;
    if (wf && !drafts[wf.id]) {
      saveDraft({
        workflowId: wf.id,
        name: wf.name,
        courseId: wf.courseId,
        plugins: wf.plugins || {},
        creatorId: user?.id,
      });
    }
  }, [courseId, query.data, user?.id]);

  return {
    workflows: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useCreateWorkflow() {
  const courseId = useWorkflowStore((s) => s.activeCourseId);
  const setActiveWorkflowId = useWorkflowStore((s) => s.setActiveWorkflowId);
  const client = useQueryClient();

  return useMutation({
    mutationFn: async (args: { name: string; description?: string; plugins?: Workflow["plugins"] }) => {
      if (!courseId) throw new Error("No active course selected");
      const payload = {
        courseId,
        name: args.name,
        description: args.description ?? "",
        plugins: args.plugins ?? {},
      };
      const res = await api.post("/workflows", payload);
      return res.data as Workflow;
    },
    onSuccess: (created) => {
      if (!courseId) return;
      client.invalidateQueries({queryKey: keys.workflows(courseId)}).then();
      setActiveWorkflowId(created.id);
    },
  });
}

export function usePersistWorkflowDrafts() {
  const client = useQueryClient();
  const { user } = useAuth();

  return useMutation({
    mutationFn: async () => {
      const { drafts } = useWorkflowStore.getState();
      const entries = Object.entries(drafts);
      if (entries.length === 0) return { updated: 0 } as { updated: number };

      // Filter drafts to only include those created by the current user
      const currentUserId = user?.id;
      const userDrafts = entries.filter(([_, draft]) => {
        // If creatorId is not set (old drafts), we skip them to avoid 403 errors
        // If creatorId matches current user, we include them
        return draft.creatorId && draft.creatorId === currentUserId;
      });

      if (userDrafts.length === 0) return { updated: 0 } as { updated: number };

      const touchedCourses = new Set<string>();

      await Promise.all(
        userDrafts.map(async ([workflowId, draft]) => {
          try {
            const payload = {
              name: draft.name,
              description: draft.description ?? "",
              plugins: draft.plugins ?? {},
            };
            await api.put(`/workflows/${workflowId}`, payload);
            touchedCourses.add(draft.courseId);
          } catch (error: any) {
            if (error?.response?.status === 404) {
              toast.error(`Can't find workflow '${draft.name || workflowId}'. It may have been deleted.`);
            } else if (error?.response?.status === 403) {
              toast.error(`You don't have permission to update workflow '${draft.name || workflowId}'.`);
            } else {
              throw error;
            }
          }
        })
      );

      touchedCourses.forEach((courseId) => {
        client.invalidateQueries({ queryKey: keys.workflows(courseId) });
      });

      return { updated: userDrafts.length } as { updated: number };
    },
  });
}

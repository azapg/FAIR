import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import api from "@/lib/api";
import { useWorkflowStore } from "@/store/workflows-store";
import type { Workflow } from "@/store/workflows-store";
import { toast } from "sonner";

const keys = {
  workflows: (courseId: string) => ["workflows", courseId] as const,
};

export function useWorkflows() {
  const drafts = useWorkflowStore((s) => s.drafts);
  const saveDraft = useWorkflowStore((s) => s.saveDraft);
  const courseId = useWorkflowStore((s) => s.activeCourseId);
  const setActiveWorkflowId = useWorkflowStore((s) => s.setActiveWorkflowId);

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
      });
    }
  }, [courseId, query.data]);

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

  return useMutation({
    mutationFn: async () => {
      const { drafts } = useWorkflowStore.getState();
      const entries = Object.entries(drafts);
      if (entries.length === 0) return { updated: 0 } as { updated: number };

      const touchedCourses = new Set<string>();

      await Promise.all(
        entries.map(async ([workflowId, draft]) => {
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
              // TODO: Because this attempts to persist all drafts, in case you switched account but your browser still has drafts
              //  from the previous user, you may get a lot of these errors. We should either remove the drafts on user switch, or just persist
              //  just the active course drafts or at least just the active workflow's draft.  
            } else {
              throw error;
            }
          }
        })
      );

      touchedCourses.forEach((courseId) => {
        client.invalidateQueries({ queryKey: keys.workflows(courseId) });
      });

      return { updated: entries.length } as { updated: number };
    },
  });
}

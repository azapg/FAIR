import {create} from 'zustand';
import {persist} from "zustand/middleware";
import {RuntimePlugin} from "@/hooks/use-plugins";

export type WorkflowRunCreate = {
  status: 'pending' | 'running' | 'success' | 'failure' | 'cancelled';
  runBy: string;
  logs: any;
  submissions: any; // TODO: submission object
}

export type WorkflowRun = WorkflowRunCreate & {
  id: string;
  workflowId: string;
  startedAt: string;
  finishedAt: string | null;
}

export type WorkflowCreate = {
  name: string;
  courseId: string;
  description?: string;
  plugins: {
    transcriber?: RuntimePlugin,
    grader?: RuntimePlugin,
    validator?: RuntimePlugin,
  }
}

export type Workflow = WorkflowCreate & {
  id: string;
  createdAt: string;
  creatorId: string;
  runs?: WorkflowRun[];
}

export type WorkflowDraft = WorkflowCreate & {
  workflowId: string;
}

type State = {
  /**
   * Represents the active workflows in each course being edited but not yet saved to the backend.
   * This allows users to make changes and see a preview before committing.
   */
  drafts: Record<string, WorkflowDraft>; // workflowId -> draft (Assumes each workflow is unique to a course, so I have to consider that for a "clone" workflow option)
  coursesActiveWorkflows: Record<string, string>; // courseId -> workflowId
  activeCourseId?: string;
  activeWorkflowId?: string;
}

type Actions = {
  setActiveCourseId: (courseId: string) => void;
  setActiveWorkflowId: (workflowId: string) => void;
  /**
   * Save or update the draft for the currently active workflow.
   * Does not persist to backend until explicitly saved.
   * @param draft The draft data to save.
   */
  saveDraft: (draft: WorkflowDraft) => void;
  clearDraft: (workflowId: string) => void;
}

export const useWorkflowStore = create<State & Actions>()(
  persist(
    (set, get) => ({
      drafts: {},
      activeCourseId: undefined,
      activeWorkflowId: undefined,
      coursesActiveWorkflows: {},
      setActiveCourseId: (courseId: string) => set({activeCourseId: courseId}),
      setActiveWorkflowId: (workflowId: string) => {
        const { activeCourseId } = get();
        set({ activeWorkflowId: workflowId });
        if (activeCourseId) {
          set((state) => ({
            coursesActiveWorkflows: {
              ...state.coursesActiveWorkflows,
              [activeCourseId]: workflowId,
            },
          }));
        }
      },
      saveDraft: (draft: WorkflowDraft) => {
        const { drafts } = get();

        const existingDraft = drafts ? drafts[draft.workflowId] : undefined;
        const updatedDraft = {
          ...existingDraft,
          ...draft,
          plugins: {
            ...existingDraft?.plugins,
            ...draft.plugins
          }
        };

        set(state => ({
          drafts: {
            ...state.drafts,
            [draft.workflowId]: updatedDraft
          }
        }));
      },
      clearDraft: (workflowId: string ) => {
        set(state => {
          const newDrafts = { ...state.drafts };
          delete newDrafts[workflowId];
          return { drafts: newDrafts };
        });
      }
    }), {
      name: 'workflows-store',
      partialize: (state) => ({
        coursesActiveWorkflows: state.coursesActiveWorkflows,
        drafts: state.drafts,
      })
    }
  )
)
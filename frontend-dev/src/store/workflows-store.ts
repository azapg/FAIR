import {create} from 'zustand';
import {persist} from "zustand/middleware";
import {Plugin, PluginType, RuntimePlugin} from "@/hooks/use-plugins";
import api from "@/lib/api";

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
    transcriber?: Plugin,
    grader?: Plugin,
    validator?: Plugin,
  }
}

export type Workflow = WorkflowCreate & {
  id: string;
  createdAt: string;
  creatorId: string;
  runs?: WorkflowRun[];
}

export type PluginSummary = Pick<RuntimePlugin, 'id' | 'version' | 'hash' | 'settings'>;

export type WorkflowDraft = {
  workflowId: string;
  name?: string;
  description?: string;
  plugins: {
    transcriber?: PluginSummary;
    grader?: PluginSummary;
    validator?: PluginSummary;
  }
}

type State = {
  workflows?: Workflow[]; // TODO: made optional for initial load, but i should probably add a "isLoaded" flag or something
  isLoadingWorkflows?: boolean;
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
  loadWorkflows: () => Promise<void>;
  createWorkflow: (name: string, description?: string) => Promise<void>;

  setActiveCourseId: (courseId: string) => void;
  setActiveWorkflowId: (workflowId: string) => void;
  getActiveWorkflow: () => Workflow | undefined;

  /**
   * Save or update the draft for the currently active workflow.
   * Does not persist to backend until explicitly saved.
   * @param draft The draft data to save.
   */
  saveDraft: (draft: WorkflowDraft) => void;
  clearDraft: (workflowId: string, plugin?: PluginType) => void;
}

export const useWorkflowStore = create<State & Actions>()(
  persist(
    (set, get) => ({
      workflows: undefined,
      drafts: {},
      activeCourseId: undefined,
      activeWorkflowId: undefined,
      coursesActiveWorkflows: {},
      isLoadingWorkflows: false,

      loadWorkflows: async () => {
        const { activeCourseId: course_id, activeWorkflowId } = get();
        if (!course_id) {
          throw new Error('No active course selected');
        }

        try {
          set({isLoadingWorkflows: true });
          const response = await api.get('/workflows', {params: {course_id: course_id}}) as { data: Workflow[] };

          if (response.data.length === 0) {
            const { createWorkflow } = get();
            await createWorkflow('Default Workflow', 'This is your default workflow. You can edit it as needed.');
          } else {
            set({workflows: response.data});
          }

          if (activeWorkflowId) {
            const exists = response.data.some(w => w.id === activeWorkflowId);
            if (!exists) {
              set({activeWorkflowId: undefined});
            }
          } else {
            const lastActiveId = get().coursesActiveWorkflows[course_id];
            if (lastActiveId) {
              const exists = response.data.some(w => w.id === lastActiveId);
              if (exists) {
                set({activeWorkflowId: lastActiveId});
              }
            }
          }
        } catch (error) {
          throw new Error('Failed to load workflows', {cause: error});
        }

        set({isLoadingWorkflows: false});
      },
      setActiveCourseId: (courseId: string) => set({activeCourseId: courseId}),
      setActiveWorkflowId: (workflowId: string) => {
        const { workflows = [], activeCourseId, activeWorkflowId } = get()
        const workflow = workflows.find(w => w.id === workflowId)

        if (workflow) {
          set({activeWorkflowId: workflowId})
          if (activeCourseId) {
            set(state => ({
              coursesActiveWorkflows: {
                ...state.coursesActiveWorkflows,
                [activeCourseId]: workflowId
              }
            }))
          }
        }
      },
      getActiveWorkflow: () => {
        const {workflows = [], activeCourseId, coursesActiveWorkflows, activeWorkflowId} = get()
        let active = workflows.find(w => w.id === activeWorkflowId)
        if (!active && activeCourseId) {
          const lastActiveId = coursesActiveWorkflows[activeCourseId]
          active = workflows.find(w => w.id === lastActiveId)
        }
        return active
      },

      createWorkflow: async (name: string, description?: string): Promise<void> => {
        const { activeCourseId, workflows = [], setActiveWorkflowId } = get()

        if (!activeCourseId) {
          throw new Error('No active course selected')
        }

        const newWorkflow: WorkflowCreate = {
          courseId: activeCourseId,
          name,
          description: description || '',
          plugins: {}
        }

        try {
          const created = await api.post('/workflows', newWorkflow) as { data: Workflow }
          set({workflows: [...workflows, created.data]})
          setActiveWorkflowId(created.data.id)
        } catch (error) {
          throw new Error('Failed to create workflow', {cause: error})
        }

      },
      saveDraft: (draft: WorkflowDraft) => {
        // TODO: I could get a workflowId param instead of relying on activeWorkflowId, or get the draft.workflowId and update that...
        const {activeWorkflowId, drafts} = get();
        if (!activeWorkflowId) {
          throw new Error('No active workflow selected');
        }

        const existingDraft = drafts ? drafts[activeWorkflowId] : undefined;
        const updatedDraft = {
          ...existingDraft,
          ...draft,
          workflowId: activeWorkflowId,
          plugins: {
            ...existingDraft?.plugins,
            ...draft.plugins
          }
        };

        set(state => ({
          drafts: {
            ...state.drafts,
            [activeWorkflowId]: updatedDraft
          }
        }));
      },
      clearDraft: (workflowId: string, plugin?: PluginType) => {}
    }), {
      name: 'WorkflowsStore',
      partialize: (state) => ({
        coursesActiveWorkflows: state.coursesActiveWorkflows,
        drafts: state.drafts,
      })
    }
  )
)
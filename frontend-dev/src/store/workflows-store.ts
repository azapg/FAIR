import {create} from 'zustand';
import {persist} from "zustand/middleware";
import {Plugin} from "@/hooks/use-plugins";
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

type State = {
  workflows: Workflow[];
  coursesActiveWorkflows: Record<string, string>; // courseId -> workflowId
  activeCourseId?: string;
  activeWorkflowId?: string;
}

type Actions = {
  setWorkflows: (workflows: Workflow[]) => void;
  setActiveCourseId: (courseId: string) => void;
  setActiveWorkflowId: (workflowId: string) => void;
  getActiveWorkflow: () => Workflow | undefined;

  createWorkflow: (name: string, description?: string) => void;

}

export const useWorkflowStore = create<State & Actions>()(
  persist(
    (set, get) => ({
      workflows: [],
      activeCourseId: undefined,
      activeWorkflowId: undefined,
      coursesActiveWorkflows: {},

      setWorkflows: (workflows: Workflow[]) => set({workflows}),
      setActiveCourseId: (courseId: string) => set({activeCourseId: courseId}),
      setActiveWorkflowId: (workflowId: string) => {
        const workflow = get().workflows.find(w => w.id === workflowId)
        if (workflow) {
          set({activeWorkflowId: workflowId})
          if (workflow.courseId) {
            set(state => ({
              coursesActiveWorkflows: {
                ...state.coursesActiveWorkflows,
                [workflow.courseId]: workflowId
              }
            }))
          }
        }
      },
      getActiveWorkflow: () => {
        // TODO: If the activeWorkflowId is not found, it might be because
        //  the workflows have not been loaded yet, or the activeWorkflowId
        //  is stale. We might need to try a reload, or clear the activeWorkflowId.
        return get().workflows.find(w => w.id === get().activeWorkflowId)
      },

      createWorkflow: async (name: string, description?: string) => {
        const newWorkflow: WorkflowCreate = {
          courseId: get().activeCourseId || 'unknown', // TODO: handle unknown better
          name,
          description: description || '',
          plugins: {}
        }

        try {
          const createdWf = await api.post('/workflows', newWorkflow) as {data: Workflow}
          set({workflows: [...get().workflows, createdWf.data]})
          get().setActiveWorkflowId(createdWf.data.id)
        } catch (error) {
          alert('Failed to create workflow. Please try again.')
        }

      }
    }), {
      name: 'WorkflowsStore',
      partialize: (state) => ({coursesActiveWorkflows: state.coursesActiveWorkflows})
    }
  )
)
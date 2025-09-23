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
  loadWorkflows: () => Promise<void>;
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

      loadWorkflows: async () => {
        const course_id = get().activeCourseId;
        if (!course_id) {
          throw new Error('No active course selected');
        }

        try {
          const response = await api.get('/workflows', {params: {course_id: course_id}}) as { data: Workflow[] };
          set({workflows: response.data});
        } catch (error) {
          throw new Error('Failed to load workflows', {cause: error});
        }
      },
      setActiveCourseId: (courseId: string) => set({activeCourseId: courseId}),
      setActiveWorkflowId: (workflowId: string) => {
        const workflow = get().workflows.find(w => w.id === workflowId)
        const activeCourseId = get().activeCourseId

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
        let active = get().workflows.find(w => w.id === get().activeWorkflowId)
        const activeCourseId = get().activeCourseId
        if (!active && activeCourseId) {
          const lastActiveId = get().coursesActiveWorkflows[activeCourseId]
          active = get().workflows.find(w => w.id === lastActiveId)
        }

        return active
      },

      createWorkflow: async (name: string, description?: string) => {
        const newWorkflow: WorkflowCreate = {
          courseId: get().activeCourseId || 'unknown', // TODO: handle unknown better
          name,
          description: description || '',
          plugins: {}
        }

        try {
          const createdWf = await api.post('/workflows', newWorkflow) as { data: Workflow }
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
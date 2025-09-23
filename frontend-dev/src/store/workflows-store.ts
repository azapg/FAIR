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
        const { workflows, activeCourseId } = get()
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
        const {workflows, activeCourseId, coursesActiveWorkflows, activeWorkflowId} = get()
        let active = workflows.find(w => w.id === activeWorkflowId)
        if (!active && activeCourseId) {
          const lastActiveId = coursesActiveWorkflows[activeCourseId]
          active = get().workflows.find(w => w.id === lastActiveId)
        }
        return active
      },

      createWorkflow: async (name: string, description?: string) => {
        const { activeCourseId, workflows, setActiveWorkflowId } = get()

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

      }
    }), {
      name: 'WorkflowsStore',
      partialize: (state) => ({coursesActiveWorkflows: state.coursesActiveWorkflows})
    }
  )
)
import {create} from 'zustand';
import {persist} from "zustand/middleware";
import {Plugin, PluginType} from "@/hooks/use-plugins";
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

  pluginsDraft: Record<string, WorkflowCreate['plugins']>; // workflowId -> WorkflowCreate.plugins
}

type Actions = {
  loadWorkflows: () => Promise<void>;
  createWorkflow: (name: string, description?: string) => void;

  setActiveCourseId: (courseId: string) => void;
  setActiveWorkflowId: (workflowId: string) => void;
  getActiveWorkflow: () => Workflow | undefined;

  saveWorkflowDraft: (pluginType: PluginType, values: Record<string, any>) => void;
  clearWorkflowDraft: (workflowId: string, plugin?: PluginType) => void;
}

export const useWorkflowStore = create<State & Actions>()(
  persist(
    (set, get) => ({
      workflows: [],
      pluginsDraft: {},
      activeCourseId: undefined,
      activeWorkflowId: undefined,
      coursesActiveWorkflows: {},

      loadWorkflows: async () => {
        const { activeCourseId: course_id, activeWorkflowId } = get();
        if (!course_id) {
          throw new Error('No active course selected');
        }

        try {
          const response = await api.get('/workflows', {params: {course_id: course_id}}) as { data: Workflow[] };
          set({workflows: response.data});

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

      },
      saveWorkflowDraft: (pluginType: PluginType, values: Record<string, any>) => {
        const {activeWorkflowId, workflows, pluginsDraft} = get()
        if (!activeWorkflowId) {
          throw new Error('No active workflow selected')
        }

        const workflow = workflows.find(w => w.id === activeWorkflowId)
        if (!workflow) {
          throw new Error('Active workflow not found')
        }

        // TODO: This just prefers the draft over the saved workflow, which might lead to lost updates
        const updatedPlugins = pluginsDraft[activeWorkflowId] ? {...pluginsDraft[activeWorkflowId]} : {...workflow.plugins}



        if (pluginType === 'transcriber') {
          updatedPlugins.transcriber = {
            ...updatedPlugins.transcriber,
            settings_schema: values
          } as Plugin
        } else if (pluginType === 'grader') {
          updatedPlugins.grader = {
            ...updatedPlugins.grader,
            settings_schema: values
          } as Plugin
        } else if (pluginType === 'validator') {
          updatedPlugins.validator = {
            ...updatedPlugins.validator,
            settings_schema: values
          } as Plugin
        }

        set(state => ({
          pluginsDraft: {
            ...state.pluginsDraft,
            [activeWorkflowId]: {...updatedPlugins}
          }
        }))
      },
      clearWorkflowDraft: (workflowId: string, plugin?: PluginType) => {
        const {pluginsDraft} = get()
        if (plugin) {
          const draft = pluginsDraft[workflowId]
          if (draft && draft[plugin]) {
            const updatedDraft = {...draft}
            delete updatedDraft[plugin]
            set(state => ({
              pluginsDraft: {
                ...state.pluginsDraft,
                [workflowId]: updatedDraft
              }
            }))
          }
        } else {
          if (pluginsDraft[workflowId]) {
            const updatedDrafts = {...pluginsDraft}
            delete updatedDrafts[workflowId]
            set(_ => ({ pluginsDraft: updatedDrafts }))
          }
        }
      }
    }), {
      name: 'WorkflowsStore',
      partialize: (state) => ({
        coursesActiveWorkflows: state.coursesActiveWorkflows,
        pluginsDraft: state.pluginsDraft,
      })
    }
  )
)
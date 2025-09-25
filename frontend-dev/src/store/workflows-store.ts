import { create } from 'zustand';
import { persist } from "zustand/middleware";

export type PluginType = "transcriber" | "grader" | "validator";

export type PluginConfig = {
  plugin_id: string;
  plugin_hash?: string;
  settings: Record<string, any>;
};

export type Plugin = {
  id: string;
  name: string;
  author: string;
  version: string;
  hash: string;
  settings_schema: any; // JSON Schema
  type: PluginType;
};

export type Workflow = {
  id: string;
  name: string;
  course_id: string;
  description?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
  plugin_configs: Record<PluginType, PluginConfig>;
};

export type WorkflowCreate = {
  name: string;
  course_id: string;
  description?: string;
  created_by: string;
  plugin_configs?: Record<PluginType, PluginConfig>;
};

type WorkflowDraft = {
  hasChanges: boolean;
  plugin_configs: Record<PluginType, PluginConfig>;
};

type State = {
  // Current workflow being edited
  currentWorkflow: Workflow | null;
  
  // All workflows for current course
  workflows: Workflow[];
  
  // Draft changes (unsaved)
  draft: WorkflowDraft;
  
  // Available plugins for selection
  availablePlugins: Record<PluginType, Plugin[]>;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  
  // Course context
  currentCourseId: string | null;
};

type Actions = {
  // Workflow management
  setCurrentCourse: (courseId: string) => void;
  loadWorkflows: () => Promise<void>;
  loadWorkflow: (workflowId: string) => Promise<void>;
  createWorkflow: (name: string, description?: string) => Promise<void>;
  
  // Draft management
  selectPlugin: (type: PluginType, pluginId: string, pluginHash?: string) => void;
  updatePluginSettings: (type: PluginType, settings: Record<string, any>) => void;
  saveDraft: () => Promise<void>;
  discardDraft: () => void;
  
  // Plugin management
  loadAvailablePlugins: (type?: PluginType) => Promise<void>;
  
  // Workflow execution
  runWorkflow: () => Promise<void>;
  
  // Utility
  clearError: () => void;
};

const initialDraft: WorkflowDraft = {
  hasChanges: false,
  plugin_configs: {}
};

export const useWorkflowStore = create<State & Actions>()(
  persist(
    (set, get) => ({
      // State
      currentWorkflow: null,
      workflows: [],
      draft: initialDraft,
      availablePlugins: {
        transcriber: [],
        grader: [],
        validator: []
      },
      isLoading: false,
      error: null,
      currentCourseId: null,

      // Actions
      setCurrentCourse: (courseId: string) => {
        set({ currentCourseId: courseId, currentWorkflow: null, draft: initialDraft });
      },

      loadWorkflows: async () => {
        const { currentCourseId } = get();
        if (!currentCourseId) {
          set({ error: "No course selected" });
          return;
        }

        set({ isLoading: true, error: null });
        try {
          // Mock API call - replace with actual API
          const response = await fetch(`/api/workflows?course_id=${currentCourseId}`);
          if (!response.ok) {
            throw new Error(`Failed to load workflows: ${response.statusText}`);
          }
          const workflows = await response.json();
          set({ workflows, isLoading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to load workflows',
            isLoading: false 
          });
        }
      },

      loadWorkflow: async (workflowId: string) => {
        set({ isLoading: true, error: null });
        try {
          // Mock API call - replace with actual API
          const response = await fetch(`/api/workflows/${workflowId}`);
          if (!response.ok) {
            throw new Error(`Failed to load workflow: ${response.statusText}`);
          }
          const workflow = await response.json();
          set({ 
            currentWorkflow: workflow, 
            draft: { hasChanges: false, plugin_configs: { ...workflow.plugin_configs } },
            isLoading: false 
          });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to load workflow',
            isLoading: false 
          });
        }
      },

      createWorkflow: async (name: string, description?: string) => {
        const { currentCourseId } = get();
        if (!currentCourseId) {
          set({ error: "No course selected" });
          return;
        }

        set({ isLoading: true, error: null });
        try {
          const workflowData: WorkflowCreate = {
            name,
            course_id: currentCourseId,
            description,
            created_by: "current-user-id", // TODO: Get from auth context
            plugin_configs: {}
          };

          // Mock API call - replace with actual API
          const response = await fetch('/api/workflows', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(workflowData)
          });
          
          if (!response.ok) {
            throw new Error(`Failed to create workflow: ${response.statusText}`);
          }
          
          const newWorkflow = await response.json();
          set(state => ({
            workflows: [...state.workflows, newWorkflow],
            currentWorkflow: newWorkflow,
            draft: { hasChanges: false, plugin_configs: {} },
            isLoading: false
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to create workflow',
            isLoading: false 
          });
        }
      },

      selectPlugin: (type: PluginType, pluginId: string, pluginHash?: string) => {
        const { availablePlugins } = get();
        const plugin = availablePlugins[type].find(p => p.id === pluginId);
        
        if (!plugin) {
          set({ error: `Plugin ${pluginId} not found` });
          return;
        }

        set(state => ({
          draft: {
            hasChanges: true,
            plugin_configs: {
              ...state.draft.plugin_configs,
              [type]: {
                plugin_id: pluginId,
                plugin_hash: pluginHash || plugin.hash,
                settings: {} // Reset settings when changing plugin
              }
            }
          },
          error: null
        }));
      },

      updatePluginSettings: (type: PluginType, settings: Record<string, any>) => {
        set(state => {
          const currentConfig = state.draft.plugin_configs[type];
          if (!currentConfig) {
            return { error: `No plugin selected for ${type}` };
          }

          return {
            draft: {
              hasChanges: true,
              plugin_configs: {
                ...state.draft.plugin_configs,
                [type]: {
                  ...currentConfig,
                  settings
                }
              }
            },
            error: null
          };
        });
      },

      saveDraft: async () => {
        const { currentWorkflow, draft } = get();
        if (!currentWorkflow) {
          set({ error: "No workflow selected" });
          return;
        }

        if (!draft.hasChanges) {
          return; // Nothing to save
        }

        set({ isLoading: true, error: null });
        try {
          // Mock API call - replace with actual API
          const response = await fetch(`/api/workflows/${currentWorkflow.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              plugin_configs: draft.plugin_configs
            })
          });
          
          if (!response.ok) {
            throw new Error(`Failed to save workflow: ${response.statusText}`);
          }
          
          const updatedWorkflow = await response.json();
          set(state => ({
            currentWorkflow: updatedWorkflow,
            workflows: state.workflows.map(w => 
              w.id === updatedWorkflow.id ? updatedWorkflow : w
            ),
            draft: { hasChanges: false, plugin_configs: draft.plugin_configs },
            isLoading: false
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to save workflow',
            isLoading: false 
          });
        }
      },

      discardDraft: () => {
        const { currentWorkflow } = get();
        set({
          draft: currentWorkflow ? {
            hasChanges: false,
            plugin_configs: { ...currentWorkflow.plugin_configs }
          } : initialDraft
        });
      },

      loadAvailablePlugins: async (type?: PluginType) => {
        set({ isLoading: true, error: null });
        try {
          const url = type ? `/api/plugins?type_filter=${type}` : '/api/plugins';
          // Mock API call - replace with actual API
          const response = await fetch(url);
          if (!response.ok) {
            throw new Error(`Failed to load plugins: ${response.statusText}`);
          }
          const plugins = await response.json();
          
          // Group plugins by type
          const pluginsByType = plugins.reduce((acc: Record<PluginType, Plugin[]>, plugin: Plugin) => {
            if (!acc[plugin.type]) {
              acc[plugin.type] = [];
            }
            acc[plugin.type].push(plugin);
            return acc;
          }, { transcriber: [], grader: [], validator: [] });

          set(state => ({
            availablePlugins: type ? 
              { ...state.availablePlugins, [type]: pluginsByType[type] || [] } :
              pluginsByType,
            isLoading: false
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to load plugins',
            isLoading: false 
          });
        }
      },

      runWorkflow: async () => {
        const { currentWorkflow, draft } = get();
        if (!currentWorkflow) {
          set({ error: "No workflow selected" });
          return;
        }

        // Use draft configs if there are unsaved changes, otherwise use saved configs
        const configsToRun = draft.hasChanges ? draft.plugin_configs : currentWorkflow.plugin_configs;

        set({ isLoading: true, error: null });
        try {
          // Mock API call - replace with actual API
          const response = await fetch('/api/workflow-runs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              workflow_id: currentWorkflow.id,
              plugin_configs: configsToRun,
              run_by: "current-user-id" // TODO: Get from auth context
            })
          });
          
          if (!response.ok) {
            throw new Error(`Failed to run workflow: ${response.statusText}`);
          }
          
          const workflowRun = await response.json();
          console.log('Workflow run started:', workflowRun);
          set({ isLoading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to run workflow',
            isLoading: false 
          });
        }
      },

      clearError: () => set({ error: null })
    }),
    {
      name: 'workflow-store',
      partialize: (state) => ({
        currentCourseId: state.currentCourseId,
      })
    }
  )
);
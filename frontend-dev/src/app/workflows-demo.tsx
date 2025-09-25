import React, { useEffect } from 'react';
import { WorkflowsSidebar } from '@/app/assignment/components/sidebar/workflows-sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';
import { useWorkflowStore } from '@/store/workflows-store';

// Mock data for demonstration
const mockWorkflows = [
  {
    id: '1',
    name: 'Basic Grading Workflow',
    course_id: 'course-1',
    description: 'Standard transcription and grading workflow',
    created_by: 'user-1',
    created_at: '2024-01-15T10:00:00Z',
    plugin_configs: {
      transcriber: {
        plugin_id: 'gpt-4-transcriber',
        plugin_hash: 'abc123',
        settings: { model: 'gpt-4', temperature: 0.1 }
      }
    }
  }
];

const mockPlugins = {
  transcriber: [
    {
      id: 'gpt-4-transcriber',
      name: 'GPT-4 Transcriber',
      author: 'OpenAI',
      version: '1.2.0',
      hash: 'abc123',
      type: 'transcriber' as const,
      settings_schema: {
        type: 'object',
        title: 'GPT-4 Settings',
        properties: {
          model: {
            type: 'string',
            title: 'Model',
            description: 'GPT model to use',
            default: 'gpt-4'
          },
          temperature: {
            type: 'number',
            title: 'Temperature',
            description: 'Randomness in responses (0-1)',
            default: 0.1,
            minimum: 0,
            maximum: 1
          }
        }
      }
    }
  ],
  grader: [],
  validator: []
};

export default function WorkflowsDemo() {
  const setCurrentCourse = useWorkflowStore(state => state.setCurrentCourse);

  useEffect(() => {
    // Set up mock course
    setCurrentCourse('course-1');
    
    // Mock API responses
    const originalFetch = window.fetch;
    window.fetch = async (url: string | URL | Request, options?: RequestInit) => {
      const urlString = url.toString();
      
      if (urlString.includes('/workflows') && !urlString.includes('/workflow')) {
        return new Response(JSON.stringify(mockWorkflows), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      if (urlString.includes('/workflows/')) {
        const workflowId = urlString.split('/').pop();
        const workflow = mockWorkflows.find(w => w.id === workflowId);
        return new Response(JSON.stringify(workflow || null), {
          status: workflow ? 200 : 404,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      if (urlString.includes('/plugins')) {
        const searchParams = new URL(urlString).searchParams;
        const typeFilter = searchParams.get('type_filter');
        
        if (typeFilter) {
          return new Response(JSON.stringify(mockPlugins[typeFilter as keyof typeof mockPlugins] || []), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        const allPlugins = [...mockPlugins.transcriber, ...mockPlugins.grader, ...mockPlugins.validator];
        return new Response(JSON.stringify(allPlugins), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      // Default to original fetch for other requests
      return originalFetch(url, options);
    };

    // Cleanup
    return () => {
      window.fetch = originalFetch;
    };
  }, [setCurrentCourse]);

  return (
    <SidebarProvider>
      <div className="flex h-screen">
        <WorkflowsSidebar side="left" className="w-80" />
        <div className="flex-1 p-8">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold mb-6">Workflow Sidebar Demo</h1>
            
            <div className="space-y-6">
              <div className="bg-card rounded-lg p-6 border">
                <h2 className="text-xl font-semibold mb-4">🎯 Features</h2>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    <span>Load and switch between workflows</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    <span>Select plugins and configure settings</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    <span>Draft system with save/discard</span>
                  </li>
                </ul>
              </div>

              <div className="bg-card rounded-lg p-6 border">
                <h2 className="text-xl font-semibold mb-4">📋 Instructions</h2>
                <ol className="space-y-2 text-sm list-decimal list-inside">
                  <li>Select a workflow from the dropdown</li>
                  <li>Expand sections and choose plugins</li>
                  <li>Modify settings and notice the draft indicators</li>
                  <li>Save or discard changes as needed</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    </SidebarProvider>
  );
}
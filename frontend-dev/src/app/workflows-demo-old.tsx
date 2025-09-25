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
        settings: {
          model: 'gpt-4',
          temperature: 0.1
        }
      },
      grader: {
        plugin_id: 'rubric-grader',
        plugin_hash: 'def456', 
        settings: {
          strict_mode: true,
          max_score: 100
        }
      }
    }
  },
  {
    id: '2',
    name: 'Advanced Analysis Workflow',
    course_id: 'course-1',
    description: 'Includes validation step',
    created_by: 'user-1',
    created_at: '2024-01-16T10:00:00Z',
    plugin_configs: {
      transcriber: {
        plugin_id: 'whisper-transcriber',
        plugin_hash: 'ghi789',
        settings: {
          language: 'en',
          model_size: 'large'
        }
      },
      grader: {
        plugin_id: 'ai-grader',
        plugin_hash: 'jkl012',
        settings: {
          use_rubric: true,
          provide_feedback: true
        }
      },
      validator: {
        plugin_id: 'plagiarism-checker',
        plugin_hash: 'mno345',
        settings: {
          threshold: 0.8,
          check_internet: true
        }
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
          },
          max_tokens: {
            type: 'number',
            title: 'Max Tokens',
            description: 'Maximum tokens to generate',
            default: 1000
          }
        }
      }
    },
    {
      id: 'whisper-transcriber',
      name: 'Whisper Transcriber',
      author: 'OpenAI',
      version: '2.1.0', 
      hash: 'ghi789',
      type: 'transcriber' as const,
      settings_schema: {
        type: 'object',
        title: 'Whisper Settings',
        properties: {
          language: {
            type: 'string',
            title: 'Language',
            description: 'Audio language',
            default: 'en'
          },
          model_size: {
            type: 'string',
            title: 'Model Size',
            description: 'Whisper model size',
            default: 'large'
          }
        }
      }
    }
  ],
  grader: [
    {
      id: 'rubric-grader',
      name: 'Rubric-Based Grader',
      author: 'FAIR Team',
      version: '1.0.0',
      hash: 'def456',
      type: 'grader' as const,
      settings_schema: {
        type: 'object',
        title: 'Rubric Grader Settings',
        properties: {
          strict_mode: {
            type: 'boolean',
            title: 'Strict Mode',
            description: 'Apply strict grading criteria',
            default: false
          },
          max_score: {
            type: 'number',
            title: 'Maximum Score',
            description: 'Maximum possible score',
            default: 100
          },
          partial_credit: {
            type: 'boolean',
            title: 'Partial Credit',
            description: 'Allow partial credit',
            default: true
          }
        }
      }
    },
    {
      id: 'ai-grader',
      name: 'AI-Powered Grader',
      author: 'FAIR Team',
      version: '2.0.0',
      hash: 'jkl012',
      type: 'grader' as const,
      settings_schema: {
        type: 'object',
        title: 'AI Grader Settings',
        properties: {
          use_rubric: {
            type: 'boolean',
            title: 'Use Rubric',
            description: 'Apply rubric-based grading',
            default: true
          },
          provide_feedback: {
            type: 'boolean',
            title: 'Provide Feedback',
            description: 'Generate feedback for students',
            default: true
          }
        }
      }
    }
  ],
  validator: [
    {
      id: 'plagiarism-checker',
      name: 'Plagiarism Checker',
      author: 'FAIR Team',
      version: '1.5.0',
      hash: 'mno345',
      type: 'validator' as const,
      settings_schema: {
        type: 'object',
        title: 'Plagiarism Checker Settings',
        properties: {
          threshold: {
            type: 'number',
            title: 'Similarity Threshold',
            description: 'Plagiarism detection threshold (0-1)',
            default: 0.8,
            minimum: 0,
            maximum: 1
          },
          check_internet: {
            type: 'boolean',
            title: 'Check Internet Sources',
            description: 'Check against internet sources',
            default: true
          }
        }
      }
    }
  ]
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
              <h2 className="text-xl font-semibold mb-4">🎯 Features Demonstrated</h2>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Load and switch between workflows</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Select plugins for each type (transcriber, grader, validator)</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Configure plugin settings with real-time updates</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Draft system with save/discard functionality</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Visual feedback for unsaved changes</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  <span>Create new workflows</span>
                </li>
              </ul>
            </div>

            <div className="bg-card rounded-lg p-6 border">
              <h2 className="text-xl font-semibold mb-4">📋 Instructions</h2>
              <ol className="space-y-2 text-sm list-decimal list-inside">
                <li>Select a workflow from the dropdown in the sidebar</li>
                <li>Expand plugin sections by clicking the section headers</li>
                <li>Choose different plugins from the dropdowns</li>
                <li>Modify plugin settings - notice the "Unsaved Changes" badge appears</li>
                <li>Use "Save Draft" to persist changes or "Discard" to revert</li>
                <li>Try creating a new workflow with the "+" button</li>
                <li>Click "Run Workflow" to execute (mock API call)</li>
              </ol>
            </div>

            <div className="bg-card rounded-lg p-6 border">
              <h2 className="text-xl font-semibold mb-4">🏗️ Architecture Highlights</h2>
              <ul className="space-y-2 text-sm">
                <li><strong>Simplified Store:</strong> Single Zustand store with clear state separation</li>
                <li><strong>Draft System:</strong> Changes are tracked separately from saved state</li>
                <li><strong>Plugin Management:</strong> Clear separation between plugin definitions and configurations</li>
                <li><strong>API Ready:</strong> Designed to work with the new simplified backend schema</li>
                <li><strong>Error Handling:</strong> Proper error states and user feedback</li>
                <li><strong>Loading States:</strong> Visual indicators for async operations</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </SidebarProvider>
  );
}
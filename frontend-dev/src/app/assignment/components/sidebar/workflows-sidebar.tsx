import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader
} from "@/components/ui/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PlusIcon, SaveIcon, RotateCcwIcon } from "lucide-react";
import { useWorkflowStore } from "@/store/workflows-store";
import PluginSection from "@/app/assignment/components/sidebar/plugin-section";
import { useEffect } from "react";

export function WorkflowsSidebar({
  side,
  className,
  ...sidebarProps
}: {
  side?: "left" | "right"
  className?: string
}) {
  const {
    currentWorkflow,
    workflows,
    draft,
    isLoading,
    error,
    currentCourseId,
    setCurrentCourse,
    loadWorkflows,
    loadWorkflow,
    createWorkflow,
    saveDraft,
    discardDraft,
    runWorkflow,
    loadAvailablePlugins,
    clearError
  } = useWorkflowStore();

  // Load workflows when course changes
  useEffect(() => {
    if (currentCourseId) {
      loadWorkflows();
      loadAvailablePlugins(); // Load all available plugins
    }
  }, [currentCourseId, loadWorkflows, loadAvailablePlugins]);

  const onCreateWorkflow = async () => {
    const name = prompt("Enter workflow name", "Untitled Workflow");
    if (name) {
      await createWorkflow(name);
    }
  };

  const onWorkflowChange = (workflowId: string) => {
    loadWorkflow(workflowId);
  };

  const onSaveDraft = () => {
    saveDraft();
  };

  const onDiscardDraft = () => {
    discardDraft();
  };

  const onRunWorkflow = () => {
    runWorkflow();
  };

  if (error) {
    return (
      <Sidebar side={side} className={className} {...sidebarProps}>
        <SidebarContent className="p-4">
          <div className="text-red-500 text-sm">
            Error: {error}
            <Button variant="outline" size="sm" onClick={clearError} className="ml-2">
              Dismiss
            </Button>
          </div>
        </SidebarContent>
      </Sidebar>
    );
  }

  if (!currentCourseId) {
    return (
      <Sidebar side={side} className={className} {...sidebarProps}>
        <SidebarContent className="p-4">
          <div className="text-muted-foreground text-sm">
            Select a course to manage workflows
          </div>
        </SidebarContent>
      </Sidebar>
    );
  }

  return (
    <Sidebar side={side} className={className} {...sidebarProps}>
      <SidebarHeader className="py-4 flex-row items-center justify-between gap-2 px-2.5">
        <div className="flex-1">
          <Select 
            value={currentWorkflow?.id || ""} 
            onValueChange={onWorkflowChange}
            disabled={isLoading}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={isLoading ? "Loading..." : "Select workflow"} />
            </SelectTrigger>
            <SelectContent position="popper" className="w-[--radix-select-trigger-width]">
              {workflows.map((w) => (
                <SelectItem key={w.id} value={w.id}>
                  {w.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button 
          variant="outline" 
          size="icon" 
          onClick={onCreateWorkflow}
          disabled={isLoading}
        >
          <PlusIcon />
        </Button>
      </SidebarHeader>
      
      <Separator />
      
      {/* Draft status indicator */}
      {draft.hasChanges && (
        <div className="px-2.5 py-2">
          <Badge variant="secondary" className="text-xs">
            Unsaved Changes
          </Badge>
        </div>
      )}
      
      <SidebarContent>
        {currentWorkflow ? (
          <>
            <PluginSection 
              title="Transcriber" 
              action="Transcribe all" 
              type="transcriber" 
            />
            <Separator />
            <PluginSection 
              title="Grader" 
              action="Grade all" 
              type="grader" 
            />
            <Separator />
            <PluginSection 
              title="Validator" 
              action="Validate all" 
              type="validator" 
            />
            <Separator />
          </>
        ) : (
          <div className="p-4 text-center text-muted-foreground text-sm">
            Select a workflow to configure plugins
          </div>
        )}
      </SidebarContent>
      
      <SidebarFooter className="py-4 px-2.5">
        <Separator />
        
        {/* Save/Discard buttons */}
        {draft.hasChanges && (
          <div className="flex gap-2 mb-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onSaveDraft}
              disabled={isLoading}
              className="flex-1"
            >
              <SaveIcon className="w-4 h-4 mr-2" />
              Save Draft
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onDiscardDraft}
              disabled={isLoading}
              className="flex-1"
            >
              <RotateCcwIcon className="w-4 h-4 mr-2" />
              Discard
            </Button>
          </div>
        )}
        
        {/* Run workflow button */}
        <Button 
          onClick={onRunWorkflow}
          disabled={isLoading || !currentWorkflow}
          className="w-full"
        >
          {isLoading ? "Running..." : "Run Workflow"}
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { LoaderIcon, PlusIcon } from "lucide-react";
import { useWorkflowStore } from "@/store/workflows-store";
import PluginSection from "@/app/assignment/components/sidebar/plugin-section";
import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useSessionStore } from "@/store/session-store";
import {
  useCreateWorkflow,
  usePersistWorkflowDrafts,
  useWorkflows,
} from "@/hooks/use-workflows";

export function WorkflowsSidebar({
  side,
  className,
  ...sidebarProps
}: {
  side?: "left" | "right";
  className?: string;
}) {
  const { workflows, isLoading } = useWorkflows();
  const drafts = useWorkflowStore((state) => state.drafts);
  const activeWorkflowId = useWorkflowStore((state) => state.activeWorkflowId);
  const setActiveWorkflowId = useWorkflowStore(
    (state) => state.setActiveWorkflowId,
  );
  const draft = activeWorkflowId ? drafts[activeWorkflowId] : undefined;
  const workflow = useMemo(() => {
    if (activeWorkflowId)
      return workflows.find((w) => w.id === activeWorkflowId);
    return workflows[0];
  }, [activeWorkflowId, workflows]);

  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);

  const [isRunning, setIsRunning] = useState(false);

  const { mutateAsync: createWorkflow } = useCreateWorkflow();
  const { mutateAsync: persistDrafts } = usePersistWorkflowDrafts();

  useEffect(() => {
    if (!activeWorkflowId && workflows.length > 0) {
      setActiveWorkflowId(workflows[0].id);
    }

    // TODO: Workflows state is so awful that creating a default workflow if none exist is too complicated for now.
    //  So I will just make the user create one manually, though I would like a better UX for this.
  }, [activeWorkflowId, workflows]);

  if (isLoading && !workflow) {
    // TODO: Skeleton loader
    return <></>;
  }

  const onCreateWorkflow = async () => {
    const name = prompt("Enter workflow name", "Untitled Workflow");
    if (name) {
      await createWorkflow({ name });
    }
  };

  const runWorkflow = async () => {
    if (isRunning || !workflow || !activeWorkflowId) return;
    setIsRunning(true);
    try {
      await persistDrafts();

      const response = await api.post("/sessions", {
        workflow_id: activeWorkflowId,
        submission_ids: [
          "4bb239473f634f5c80c5887554180d2d",
          "21b9196d7e154ecd881910a0389cd7a0",
          "a28d0dab9ba143e283be47d6d58d558a",
        ],
      });
      setCurrentSession(response.data.session);
    } catch (error) {
      console.error("Failed to start workflow run", error);
    }
  };

  return (
    <Sidebar side={side} className={className} {...sidebarProps}>
      <SidebarHeader className="py-4 flex-row items-center justify-between gap-2 px-2.5">
        <Select value={workflow?.id} onValueChange={setActiveWorkflowId}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select workflow" />
          </SelectTrigger>
          <SelectContent
            position="popper"
            className="w-[--radix-select-trigger-width]"
          >
            {workflows.map((w) => (
              <SelectItem key={w.id} value={w.id}>
                {w.name}
              </SelectItem>
            ))}
            {workflows.length === 0 && (
              <SelectItem value="no-workflows" disabled>
                No workflows available
              </SelectItem>
            )}
          </SelectContent>
        </Select>

        <Button variant="outline" size="icon" onClick={onCreateWorkflow}>
          <PlusIcon />
        </Button>
      </SidebarHeader>
      <Separator />
      {workflow && draft ? (
        <>
          <SidebarContent>
            <PluginSection
              title={"Transcriber"}
              action={"Transcribe all"}
              type={"transcriber"}
            />
            <Separator />
            <PluginSection
              title={"Grader"}
              action={"Grade all"}
              type={"grader"}
            />
            <Separator />
            <PluginSection
              title={"Validator"}
              action={"Validate all"}
              type={"validator"}
            />
            <Separator />
          </SidebarContent>
          <SidebarFooter className={"py-4 px-2.5"}>
            <Separator />
            <Button onClick={runWorkflow} disabled={isRunning}>
              {isRunning ? (
                <>
                  <LoaderIcon className={"animate-spin"} /> Running
                </>
              ) : (
                <>Run Workflow</>
              )}
            </Button>
          </SidebarFooter>
        </>
      ) : (
        <div className="p-4 text-sm text-muted-foreground h-full flex flex-col items-center justify-center text-center gap-2">
          {workflows.length === 0 ? (
            <div>
              <p>No workflows available.</p>
              <p>Create one using the "+" button above.</p>
            </div>
          ) : !activeWorkflowId ? (
            <div>
              <p>No workflow selected.</p>
              <p>Select one from the dropdown above.</p>
            </div>
          ) : (
            <div>Workflow details go here.</div>
          )}
        </div>
      )}
    </Sidebar>
  );
}

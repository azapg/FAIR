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
import {
  ChevronDownIcon,
  Clock,
  LoaderIcon,
  PlusIcon,
  Save,
  Ban,
} from "lucide-react";
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
import { ButtonGroup } from "@/components/ui/button-group";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ExecutionLogsView } from "@/app/assignment/components/sidebar/execution-logs-view";
import { useSubmissions } from "@/hooks/use-submissions";
import { toast } from "sonner"
import { useTranslation } from "react-i18next";

export function WorkflowsSidebar({
  side,
  assignmentId,
  className,
  ...sidebarProps
}: {
  side?: "left" | "right";
  className?: string;
  assignmentId: string;
}) {
  const { workflows } = useWorkflows();
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
  const {data: submissions} = useSubmissions({assignment_id: assignmentId})
  const { t } = useTranslation();

  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);
  const clearLogs = useSessionStore((state) => state.clearLogs);
  const currentSession = useSessionStore((state) => state.currentSession);

  const [isRunning, setIsRunning] = useState(false);
  const [showLogs, setShowLogs] = useState(false);

  const { mutateAsync: createWorkflow } = useCreateWorkflow();
  const { mutateAsync: persistDrafts } = usePersistWorkflowDrafts();

  useEffect(() => {
    if (!activeWorkflowId && workflows.length > 0) {
      setActiveWorkflowId(workflows[0].id);
    }

    // TODO: Workflows state is so awful that creating a default workflow if none exist is too complicated for now.
    //  So I will just make the user create one manually, though I would like a better UX for this.
  }, [activeWorkflowId, workflows]);

  // Remove early return so footer is always visible even while loading

  const onCreateWorkflow = async () => {
    const name = prompt("Enter workflow name", "Untitled Workflow");
    if (name) {
      await createWorkflow({ name });
    }
  };

  const runWorkflow = async () => {
    if (isRunning || !workflow || !activeWorkflowId) return;
    setIsRunning(true);
    // Open logs immediately and clear any stale logs to avoid flicker from previous sessions
    clearLogs();
    setShowLogs(true);
    try {
      await persistDrafts();

      const response = await api.post("/sessions", {
        workflow_id: activeWorkflowId,
        submission_ids: submissions?.map(s => s.id) || [],
      });
      setCurrentSession(response.data.session);
    } catch (error) {
      console.error("Failed to start workflow run", error);
      setIsRunning(false);
      setShowLogs(false);
      toast.error(t("workflow.failedToStart"));
    }
  };

  // When the session ends (SessionSocketProvider sets it to null on close), stop showing running state
  useEffect(() => {
    if (!currentSession) {
      setIsRunning(false);
    }
  }, [currentSession?.id]);

  return (
    <Sidebar side={side} className={className} {...sidebarProps}>
      {showLogs ? null : (
        <SidebarHeader className="py-4 flex-row items-center justify-between gap-2 px-2.5">
          <Select value={workflow?.id} onValueChange={setActiveWorkflowId}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder={t("workflow.selectWorkflow")} />
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
                  {t("workflow.noWorkflows")}
                </SelectItem>
              )}
            </SelectContent>
          </Select>

          <Button variant="outline" size="icon" onClick={onCreateWorkflow}>
            <PlusIcon />
          </Button>
        </SidebarHeader>
      )}
      <Separator />
      {showLogs ? (
        <ExecutionLogsView onBack={() => setShowLogs(false)} />
      ) : workflow && draft ? (
        <>
          <SidebarContent>
            <PluginSection
              title={t("plugins.transcriber")}
              action={t("plugins.transcribeAll")}
              type={"transcriber"}
            />
            <Separator />
            <PluginSection
              title={t("plugins.grader")}
              action={t("plugins.gradeAll")}
              type={"grader"}
            />
            <Separator />
            <PluginSection
              title={t("plugins.validator")}
              action={t("plugins.validateAll")}
              type={"validator"}
            />
            <Separator />
          </SidebarContent>
        </>
      ) : (
        <div className="p-4 text-sm text-muted-foreground h-full flex flex-col items-center justify-center text-center gap-2">
          {workflows.length === 0 ? (
            <div>
              <p>{t("workflow.noWorkflows")}</p>
              <p>{t("workflow.createWithButton")}</p>
            </div>
          ) : !activeWorkflowId ? (
            <div>
              <p>{t("workflow.noWorkflowSelected")}</p>
              <p>{t("workflow.selectFromDropdown")}</p>
            </div>
          ) : (
            <div>{t("workflow.workflowDetails")}</div>
          )}
        </div>
      )}
      {/* Footer is always visible */}
      <SidebarFooter className={"px-2.5"}>
        <Separator />
        <WorkflowSidebarRunButton
          isRunning={isRunning}
          onRun={runWorkflow}
          onShowLogs={() => setShowLogs(true)}
        />
      </SidebarFooter>
    </Sidebar>
  );
}

const WorkflowSidebarRunButton = ({
  isRunning,
  onRun,
  onShowLogs,
}: {
  isRunning: boolean;
  onRun: () => void;
  onShowLogs: () => void;
}) => {
  const { t } = useTranslation();
  
  return (
    <ButtonGroup className="flex w-full my-2">
      <Button
        onClick={onRun}
        disabled={isRunning}
        className="flex-1"
        variant="outline"
      >
        {isRunning ? (
          <>
            <LoaderIcon className={"animate-spin"} /> {t("workflow.running")}
          </>
        ) : (
          <>{t("workflow.runWorkflow")}</>
        )}
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline">
            <ChevronDownIcon />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuGroup>
            <DropdownMenuItem onClick={onShowLogs}>
              <Clock /> {t("workflow.viewLogs")}
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Save /> {t("workflow.saveWorkflow")}
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem disabled={!isRunning} variant="destructive">
              <Ban /> {t("workflow.abortWorkflow")}
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </ButtonGroup>
  );
};

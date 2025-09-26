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
import {Separator} from "@/components/ui/separator"
import {Button} from "@/components/ui/button"
import {PlusIcon} from "lucide-react";
import {useWorkflowStore} from "@/store/workflows-store";
import PluginSection from "@/app/assignment/components/sidebar/plugin-section";
import {Tooltip, TooltipContent, TooltipTrigger} from "@/components/ui/tooltip";


export function WorkflowsSidebar({
                                   side,
                                   className,
                                   ...sidebarProps
                                 }: {
  side?: "left" | "right"
  className?: string
}) {
  const {workflows, createWorkflow, getActiveWorkflow, setActiveWorkflowId} = useWorkflowStore();
  const workflow = getActiveWorkflow();

  const onCreateWorkflow = () => {
    const name = prompt("Enter workflow name", "Untitled Workflow");
    if (name) {
      createWorkflow(name);
    }
  }

  return (
    <Sidebar side={side} className={className} {...sidebarProps}>
      <SidebarHeader className="py-4 flex-row items-center justify-between gap-2 px-2.5">
        <Select value={workflow?.id} onValueChange={setActiveWorkflowId}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select workflow"/>
          </SelectTrigger>
          <SelectContent position="popper" className="w-[--radix-select-trigger-width]">
            {workflows.map((w) => (
              <SelectItem key={w.id} value={w.id}>
                {w.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" size="icon" onClick={onCreateWorkflow} disabled>
              <PlusIcon/>
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>This feature is disabled during beta preview.</p>
          </TooltipContent>
        </Tooltip>
      </SidebarHeader>
      <Separator/>
      <SidebarContent>
        <PluginSection title={"Transcriber"} action={"Transcribe all"} type={"transcriber"} />
        <Separator/>
        <PluginSection title={"Grader"} action={"Grade all"} type={"grader"} />
        <Separator/>
        <PluginSection title={"Validator"} action={"Validate all"} type={"validator"} />
        <Separator/>
      </SidebarContent>
      <SidebarFooter className={"py-4 px-2.5"}>
        <Separator/>
        <Button>Run Workflow</Button>
      </SidebarFooter>
    </Sidebar>
  )
}
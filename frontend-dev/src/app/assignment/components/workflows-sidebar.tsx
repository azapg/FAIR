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
import TranscriberSection from "./transcriber-section"
import GraderSection from "./grader-section"
import ValidatorSection from "./validator-section"
import {PlusIcon} from "lucide-react";
import {useWorkflowStore} from "@/store/workflows-store";
import {useAuth} from "@/contexts/auth-context";


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

  const {user, isAuthenticated} = useAuth();

  if (!isAuthenticated || !user) {
    return null; // TODO: i do need to handle this better
  }

  const onCreateWorkflow = () => {
    const name = prompt("Enter workflow name", "Untitled Workflow");
    if (name) {
      createWorkflow(name, user.id);
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

        <Button variant="outline" size="icon" onClick={onCreateWorkflow}>
          <PlusIcon/>
        </Button>
      </SidebarHeader>
      <Separator/>
      <SidebarContent>
        <TranscriberSection/>
        <Separator/>
        <GraderSection/>
        <Separator/>
        <ValidatorSection/>
        <Separator/>
      </SidebarContent>
      <SidebarFooter className={"py-4 px-2.5"}>
        <Separator/>
        <Button>Run Workflow</Button>
      </SidebarFooter>
    </Sidebar>
  )
}
"use client"
import {useState} from "react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {Separator} from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import TranscriberSection from "./transcriber-section"
import GraderSection from "./grader-section"
import ValidatorSection from "./validator-section"

const workflows = [
  {id: "1", name: "Workflow 1"},
  {id: "2", name: "Workflow 2"},
  {id: "3", name: "Workflow 3"},
]

export function WorkflowsSidebar({
                                   side,
                                   className,
                                   ...sidebarProps
                                 }: {
  side?: "left" | "right"
  className?: string
  [key: string]: any // eslint-disable-line @typescript-eslint/no-explicit-any
}) {
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>(workflows[0]?.id)

  return (
    <Sidebar side={side} className={className} {...sidebarProps}>
      <SidebarHeader className="py-5">
        <SidebarMenu>
          <SidebarMenuItem>
            <Select value={selectedWorkflowId} onValueChange={setSelectedWorkflowId}>
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
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <Separator/>
      <SidebarContent>
        <TranscriberSection />
        <Separator/>
        <GraderSection />
        <Separator/>
        <ValidatorSection />
        <Separator/>
      </SidebarContent>
      <SidebarFooter className={"py-4 px-2.5"}>
        <Separator/>
        <Button >Run Workflow</Button>
      </SidebarFooter>
    </Sidebar>
  )
}
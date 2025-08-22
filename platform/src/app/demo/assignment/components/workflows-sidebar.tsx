"use client"
import { useState } from "react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarGroupLabel, SidebarGroupContent,
} from "@/components/ui/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ChevronDown } from "lucide-react"
import {Collapsible, CollapsibleContent, CollapsibleTrigger} from "@/components/ui/collapsible";

const workflows = [
  { id: "1", name: "Workflow 1" },
  { id: "2", name: "Workflow 2" },
  { id: "3", name: "Workflow 3" },
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
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <Select value={selectedWorkflowId} onValueChange={setSelectedWorkflowId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select workflow" />
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
      <SidebarContent>
        <Collapsible defaultOpen className="group/collapsible">
          <SidebarGroup>
            <SidebarGroupLabel>
              <CollapsibleTrigger  className={"flex flex-row items-center gap-1"}>
                Transcriber
                <ChevronDown className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-180" size={14}/>
              </CollapsibleTrigger>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent className={"pl-2"}>
                Hi, I&#39;m a Transcriber
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>

        <Collapsible defaultOpen className="group/collapsible">
          <SidebarGroup>
            <SidebarGroupLabel>
              <CollapsibleTrigger  className={"flex flex-row items-center gap-1"}>
                Grader
                <ChevronDown className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-180" size={14}/>
              </CollapsibleTrigger>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent className={"pl-2"}>
                Hi, I&#39;m a Grader
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>

        <Collapsible defaultOpen className="group/collapsible">
          <SidebarGroup>
            <SidebarGroupLabel>
              <CollapsibleTrigger  className={"flex flex-row items-center gap-1"}>
                Validator
                <ChevronDown className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-180" size={14}/>
              </CollapsibleTrigger>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent className={"pl-2"}>
                Hi, I&#39;m a Validator
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  )
}
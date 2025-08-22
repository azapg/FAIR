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
import {Button} from "@/components/ui/button";

const workflows = [
  { id: "1", name: "Workflow 1" },
  { id: "2", name: "Workflow 2" },
  { id: "3", name: "Workflow 3" },
]

// TODO: action buttons (transcribe, grade, validate) should have scopes (all, selected, etc.) and modes.
//  probably a button group with a dropdown for scope and a dropdown for mode.
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
              <SidebarGroupContent className={"flex flex-col pl-2 gap-2"}>
                Hi, I&#39;m a Transcriber
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium mb-1">Force Language</label>
                  <Select defaultValue="auto">
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="auto" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">auto</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Spanish</SelectItem>
                      <SelectItem value="fr">French</SelectItem>
                      <SelectItem value="de">German</SelectItem>
                      <SelectItem value="zh">Chinese</SelectItem>
                      <SelectItem value="ar">Arabic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button className="flex-1">Transcribe all</Button>
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
              <SidebarGroupContent className={"flex flex-col pl-2 gap-2"}>
                Hi, I&#39;m a Grader
                <Button className="flex-1">Grade all</Button>
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
              <SidebarGroupContent className={"flex flex-col pl-2 gap-2"}>
                Hi, I&#39;m a Validator
                <Button className="flex-1">Validate all</Button>
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>
      </SidebarContent>
      <SidebarFooter>
        <Button>Run Workflow</Button>
      </SidebarFooter>
    </Sidebar>
  )
}
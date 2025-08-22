"use client"
import {useState} from "react"
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
import {Plus} from "lucide-react"
import {Collapsible, CollapsibleContent, CollapsibleTrigger} from "@/components/ui/collapsible";
import {Button} from "@/components/ui/button";
import {Slider} from "@/components/ui/slider";
import {Textarea} from "@/components/ui/textarea";
import {Separator} from "@/components/ui/separator"

const workflows = [
  {id: "1", name: "Workflow 1"},
  {id: "2", name: "Workflow 2"},
  {id: "3", name: "Workflow 3"},
]

type SectionTriggerProps = {
  label: string
  className?: string
  iconSize?: number
}

function SectionTrigger({label, className, iconSize = 12}: SectionTriggerProps) {
  return (
    <CollapsibleTrigger
      className={`group/trigger flex w-full justify-between items-center px-1 text-base ${className ?? ""}`}
    >
      <span>{label}</span>
      <span className="relative inline-flex w-4 h-4 shrink-0 items-center justify-center">
        <Plus
          size={iconSize}
          className="
            origin-center transition-all duration-200
            group-data-[state=closed]/collapsible:rotate-0 group-data-[state=open]/collapsible:rotate-45
          "
        />
      </span>
    </CollapsibleTrigger>
  )
}

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
  const [graderTemperature, setGraderTemperature] = useState<number>(0.5)
  const [validatorTemperature, setValidatorTemperature] = useState<number>(0.2)

  // Reference values for temperature
  const temperatureRefs = [
    {value: 0, label: "Deterministic"},
    {value: 0.5, label: "Balanced"},
    {value: 1, label: "Creative"}
  ]

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
        <Collapsible defaultOpen className="group/collapsible">
          <SidebarGroup className="group/section">
            <SidebarGroupLabel>
              <SectionTrigger label="Transcriber"/>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent className={"flex flex-col pl-2 gap-3"}>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium mb-1">Force Language</label>
                  <Select defaultValue="auto">
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="auto"/>
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

        <Separator/>

        <Collapsible defaultOpen className="group/collapsible">
          <SidebarGroup className="group/section">
            <SidebarGroupLabel>
              <SectionTrigger label="Grader"/>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent className={"flex flex-col pl-2 gap-3"}>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium mb-1">Rubric</label>
                  <Textarea
                    className="w-full rounded px-3 py-2 text-sm resize-y min-h-[48px] bg-background"
                    placeholder="Add rubric or {{rubric-template}}"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium mb-1">Temperature</label>
                    <span className="text-xs text-muted-foreground ml-2">{graderTemperature.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[graderTemperature]}
                    min={0}
                    max={1}
                    step={0.01}
                    onValueChange={vals => setGraderTemperature(vals[0])}
                  />
                  <div className="flex flex-row justify-between text-[10px] text-muted-foreground mt-1">
                    {temperatureRefs.map(ref => (
                      <span key={ref.value}>{ref.label} ({ref.value})</span>
                    ))}
                  </div>
                </div>
                <Button className="flex-1">Grade all</Button>
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>

        <Separator/>

        <Collapsible defaultOpen className="group/collapsible">
          <SidebarGroup className="group/section">
            <SidebarGroupLabel>
              <SectionTrigger label="Validator"/>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent className={"flex flex-col pl-2 gap-3"}>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium mb-1">Temperature</label>
                    <span className="text-xs text-muted-foreground ml-2">{validatorTemperature.toFixed(2)}</span>
                  </div>
                  <Slider
                    value={[validatorTemperature]}
                    min={0}
                    max={1}
                    step={0.01}
                    onValueChange={vals => setValidatorTemperature(vals[0])}
                  />
                  <div className="flex flex-row justify-between text-[10px] text-muted-foreground mt-1">
                    {temperatureRefs.map(ref => (
                      <span key={ref.value}>{ref.label} ({ref.value})</span>
                    ))}
                  </div>
                </div>
                <Button className="flex-1">Validate all</Button>
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>
        <Separator/>
      </SidebarContent>
      <SidebarFooter>
        <Button>Run Workflow</Button>
      </SidebarFooter>
    </Sidebar>
  )
}
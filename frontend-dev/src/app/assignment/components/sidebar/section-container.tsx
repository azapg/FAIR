"use client"
import {Collapsible, CollapsibleContent} from "@/components/ui/collapsible"
import {SidebarGroup, SidebarGroupContent, SidebarGroupLabel} from "@/components/ui/sidebar"
import SectionTrigger from "./section-trigger"
import {PropsWithChildren} from "react"

export type SectionContainerProps = PropsWithChildren<{
  title: string
  defaultOpen?: boolean
  className?: string
}>

export default function SectionContainer({title, defaultOpen = true, className, children}: SectionContainerProps) {
  return (
    <Collapsible defaultOpen={defaultOpen} className="group/collapsible">
      <SidebarGroup className={`group/section ${className ?? ""}`}>
        <SidebarGroupLabel>
          <SectionTrigger title={title}/>
        </SidebarGroupLabel>
        <CollapsibleContent>
          <SidebarGroupContent className="flex flex-col pt-2 px-2 gap-6">
            {children}
          </SidebarGroupContent>
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  )
}


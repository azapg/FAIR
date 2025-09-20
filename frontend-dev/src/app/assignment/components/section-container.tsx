"use client"
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible"
import { SidebarGroup, SidebarGroupContent, SidebarGroupLabel } from "@/components/ui/sidebar"
import SectionTrigger from "./section-trigger"
import { PropsWithChildren } from "react"

export type SectionContainerProps = PropsWithChildren<{
  selectedPlugin?: string
  pluginOptions: string[]
  defaultOpen?: boolean
  className?: string
  onSelectPluginChange?: (plugin: string) => void
}>

export default function SectionContainer({ defaultOpen = true, className, children, selectedPlugin, pluginOptions, onSelectPluginChange }: SectionContainerProps) {
  return (
    <Collapsible defaultOpen={defaultOpen} className="group/collapsible">
      <SidebarGroup className={`group/section ${className ?? ""}`}>
        <SidebarGroupLabel>
          <SectionTrigger selectedPlugin={selectedPlugin} pluginOptions={pluginOptions} onSelectPluginChange={onSelectPluginChange} />
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


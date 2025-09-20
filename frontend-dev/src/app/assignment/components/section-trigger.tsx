"use client"
import { CollapsibleTrigger } from "@/components/ui/collapsible"
import { Select, SelectTrigger, SelectItem, SelectContent, SelectValue } from "@/components/ui/select"
import { Plus } from "lucide-react"

export type SectionTriggerProps = {
  selectedPlugin?: string
  pluginOptions: string[]
  className?: string
  iconSize?: number
  onSelectPluginChange?: (plugin: string) => void
}

export function SectionTrigger({ selectedPlugin, pluginOptions, className, iconSize = 12, onSelectPluginChange }: SectionTriggerProps) {
  return (
    <CollapsibleTrigger
      className={`group/trigger flex w-full justify-between items-center text-base text-foreground cursor-pointer ${className ?? ""}`}
    >
        <Select value={selectedPlugin} onValueChange={onSelectPluginChange}>
          <SelectTrigger className="w-3/4" size={"sm"}>
            <SelectValue placeholder="Select plugin" />
          </SelectTrigger>
          <SelectContent position="popper" className="w-[--radix-select-trigger-width]">
            {pluginOptions.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>


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

export default SectionTrigger


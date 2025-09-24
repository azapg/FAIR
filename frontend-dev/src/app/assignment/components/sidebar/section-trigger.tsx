"use client"
import { CollapsibleTrigger } from "@/components/ui/collapsible"
import { Plus } from "lucide-react"

export type SectionTriggerProps = {
  title: string
  className?: string
  iconSize?: number
}

export function SectionTrigger({ title, className, iconSize = 12 }: SectionTriggerProps) {
  return (
    <CollapsibleTrigger
      className={`group/trigger flex w-full justify-between items-center text-base text-foreground cursor-pointer ${className ?? ""}`}
    >
      <span>{title}</span>
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


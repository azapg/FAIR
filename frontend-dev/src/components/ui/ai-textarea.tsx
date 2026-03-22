import * as React from "react"

import { cn } from "@/lib/utils"
import { Textarea } from "@/components/ui/textarea"

// Matches the project's AI color language: amber → cyan (mirrors the rubric dialog gradient)
const AI_GRADIENT =
  "conic-gradient(from var(--ai-angle), oklch(0.78 0.16 75), oklch(0.75 0.17 130), oklch(0.73 0.18 185), oklch(0.75 0.17 220), oklch(0.78 0.16 75))"

export interface AiTextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  containerClassName?: string;
}

const AiTextarea = React.forwardRef<HTMLTextAreaElement, AiTextareaProps>(
  ({ className, containerClassName, ...props }, ref) => {
    return (
      <div className={cn("relative isolate", containerClassName)}>
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-10 rounded-[var(--radius)] blur-sm opacity-50 animate-ai-glow"
          style={{ background: AI_GRADIENT }}
        />
        <Textarea
          ref={ref}
          className={cn("bg-background dark:bg-background", className)}
          {...props}
        />
      </div>
    )
  }
)
AiTextarea.displayName = "AiTextarea"

export { AiTextarea }

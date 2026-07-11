import * as React from "react"
import { cn } from "@/lib/utils"

export interface BubbleProps extends React.ComponentProps<"div"> {
  variant?: "primary" | "secondary" | "muted" | "ghost"
  role?: "user" | "assistant" | "system"
}

export const Bubble = React.forwardRef<HTMLDivElement, BubbleProps>(
  ({ className, variant, role = "assistant", children, ...props }, ref) => {
    // Determine styles based on variant and role
    const getStyles = () => {
      if (variant) {
        switch (variant) {
          case "primary":
            return "bg-primary text-primary-foreground border border-transparent shadow-xs"
          case "secondary":
            return "bg-secondary text-secondary-foreground border border-transparent shadow-xs"
          case "muted":
            return "bg-muted text-muted-foreground border border-transparent"
          case "ghost":
            return "bg-transparent text-foreground border border-border"
        }
      }

      // Default role-based styling if no explicit variant is passed
      switch (role) {
        case "user":
          return "bg-muted text-foreground px-5 py-3.5 rounded-3xl rounded-tr-md shadow-sm border border-border/40 selection:bg-foreground/20"
        case "assistant":
          return "bg-card text-foreground px-6 py-4.5 rounded-3xl rounded-tl-md shadow-xs border border-border/80 selection:bg-primary/20"
        case "system":
          return "bg-muted/50 text-muted-foreground px-4 py-3 rounded-2xl text-xs border border-border/30 text-center"
      }
    };

    return (
      <div
        ref={ref}
        className={cn(
          "w-fit max-w-[85%] sm:max-w-[75%] leading-relaxed text-[15px]",
          getStyles(),
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
Bubble.displayName = "Bubble"

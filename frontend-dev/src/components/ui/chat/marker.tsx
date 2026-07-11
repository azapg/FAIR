import * as React from "react"
import { cn } from "@/lib/utils"

export interface MarkerProps extends React.ComponentProps<"div"> {
  variant?: "system" | "date" | "tool" | "error"
}

export const Marker = React.forwardRef<HTMLDivElement, MarkerProps>(
  ({ className, variant = "system", children, ...props }, ref) => {
    const getStyles = () => {
      switch (variant) {
        case "date":
          return "text-[10px] font-semibold text-muted-foreground uppercase tracking-widest bg-muted px-2.5 py-1 rounded-full border border-border/30"
        case "tool":
          return "text-xs font-mono text-muted-foreground bg-muted/40 border border-border/60 px-3 py-1.5 rounded-lg flex items-center gap-2"
        case "error":
          return "text-xs font-medium text-destructive bg-destructive/5 border border-destructive/20 px-3.5 py-2 rounded-xl flex items-center gap-2"
        case "system":
        default:
          return "text-xs text-muted-foreground/80 font-medium bg-muted/20 px-3 py-1.5 rounded-xl border border-border/40"
      }
    }

    return (
      <div
        ref={ref}
        className={cn("flex w-full justify-center my-4 select-none", className)}
        {...props}
      >
        <div className={cn("max-w-[90%] sm:max-w-[80%]", getStyles())}>
          {children}
        </div>
      </div>
    )
  }
)
Marker.displayName = "Marker"

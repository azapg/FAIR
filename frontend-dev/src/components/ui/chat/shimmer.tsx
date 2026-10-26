import * as React from "react"
import { cn } from "@/lib/utils"

export interface ShimmerProps extends React.ComponentProps<"div"> {
  variant?: "skeleton" | "typing"
  rows?: number
}

export const Shimmer = React.forwardRef<HTMLDivElement, ShimmerProps>(
  ({ className, variant = "typing", rows = 3, ...props }, ref) => {
    if (variant === "typing") {
      return (
        <div
          ref={ref}
          className={cn(
            "flex items-center gap-1.5 px-4.5 py-3 rounded-2xl bg-card border border-border/80 shadow-xs w-fit select-none",
            className
          )}
          {...props}
        >
          <div className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.3s]"></div>
          <div className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.15s]"></div>
          <div className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce"></div>
        </div>
      )
    }

    return (
      <div
        ref={ref}
        className={cn("w-full max-w-lg space-y-2.5 animate-pulse select-none", className)}
        {...props}
      >
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-3.5 bg-muted rounded-md",
              i === rows - 1 ? "w-[65%]" : "w-full"
            )}
            style={{
              animationDelay: `${i * 100}ms`,
            }}
          />
        ))}
      </div>
    )
  }
)
Shimmer.displayName = "Shimmer"

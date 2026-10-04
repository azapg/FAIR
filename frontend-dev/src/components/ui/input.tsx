import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "file:text-foreground placeholder:text-muted-foreground/80 selection:bg-primary selection:text-primary-foreground border-border/75 flex h-9 w-full min-w-0 rounded-[8px] border bg-[var(--field)] px-3 py-1 text-[0.8125rem] shadow-[inset_0_1px_2px_oklch(0_0_0/0.035)] transition-[background-color,border-color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "hover:border-border focus-visible:border-ring/70 focus-visible:bg-[var(--surface-raised)] focus-visible:ring-2 focus-visible:ring-ring/15",
        "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
        className
      )}
      {...props}
    />
  )
}

export { Input }

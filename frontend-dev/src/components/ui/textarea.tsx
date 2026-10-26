import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "border-border/75 placeholder:text-muted-foreground/80 flex field-sizing-content min-h-20 w-full rounded-[8px] border bg-[var(--field)] px-3 py-2 text-[0.8125rem] leading-5 shadow-[inset_0_1px_2px_oklch(0_0_0/0.035)] transition-[background-color,border-color,box-shadow] outline-none hover:border-border focus-visible:border-ring/70 focus-visible:bg-[var(--surface-raised)] focus-visible:ring-2 focus-visible:ring-ring/15 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }

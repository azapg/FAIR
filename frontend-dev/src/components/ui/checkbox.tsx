import * as React from "react"

import { cn } from "@/lib/utils"

type CheckboxProps = Omit<React.ComponentPropsWithoutRef<"input">, "type"> & {
  checked?: boolean | "indeterminate"
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, onCheckedChange, ...props }, ref) => {
    const innerRef = React.useRef<HTMLInputElement | null>(null)

    React.useImperativeHandle(ref, () => innerRef.current as HTMLInputElement)

    React.useEffect(() => {
      if (innerRef.current) {
        innerRef.current.indeterminate = checked === "indeterminate"
      }
    }, [checked])

    return (
      <input
        ref={innerRef}
        type="checkbox"
        role="checkbox"
        className={cn(
          "h-4 w-4 shrink-0 rounded-[4px] border border-primary",
          "text-primary shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        checked={checked === "indeterminate" ? false : checked}
        onChange={(event) => onCheckedChange?.(event.target.checked)}
        {...props}
      />
    )
  },
)

Checkbox.displayName = "Checkbox"

export { Checkbox }

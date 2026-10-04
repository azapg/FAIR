import * as React from "react"

import { useIsMobile } from "@/hooks/use-mobile"
import { DialogContent } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

/**
 * Full-screen page layout for mobile: content is anchored to the top of the
 * viewport so the on-screen keyboard never covers inputs, and the rest of the
 * screen stays empty (native-app style). On desktop it renders the regular
 * centered dialog.
 */
const MOBILE_SCREEN_CLASSES =
  "!inset-0 !top-0 !left-0 !flex !h-dvh !max-h-none !w-screen !max-w-none !translate-x-0 !translate-y-0 !flex-col !overflow-y-auto !rounded-none !border-0 !pb-[calc(1.5rem+env(safe-area-inset-bottom))] !shadow-none data-[state=closed]:!zoom-out-100 data-[state=open]:!zoom-in-100"

export function ResponsiveDialogContent({
  className,
  ...props
}: React.ComponentProps<typeof DialogContent>) {
  const isMobile = useIsMobile()

  return (
    <DialogContent
      className={cn(isMobile && MOBILE_SCREEN_CLASSES, className)}
      {...props}
    />
  )
}

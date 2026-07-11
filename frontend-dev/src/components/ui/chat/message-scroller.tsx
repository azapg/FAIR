import * as React from "react"
import { 
  MessageScroller as PrimitiveScroller,
  useMessageScrollerScrollable,
  useMessageScroller,
  useMessageScrollerVisibility
} from "@shadcn/react/message-scroller"
import { cn } from "@/lib/utils"
import { ArrowDown } from "lucide-react"

export const MessageScrollerProvider = PrimitiveScroller.Provider

export const MessageScroller = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof PrimitiveScroller.Root>
>(({ className, children, ...props }, ref) => (
  <PrimitiveScroller.Root
    ref={ref}
    className={cn("relative flex flex-col w-full h-full overflow-hidden", className)}
    {...props}
  >
    {children}
  </PrimitiveScroller.Root>
))
MessageScroller.displayName = "MessageScroller"

export const MessageScrollerViewport = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof PrimitiveScroller.Viewport>
>(({ className, children, ...props }, ref) => (
  <PrimitiveScroller.Viewport
    ref={ref}
    className={cn(
      "flex-1 w-full overflow-y-auto scroll-smooth custom-scrollbar focus-visible:outline-hidden",
      className
    )}
    {...props}
  >
    {children}
  </PrimitiveScroller.Viewport>
))
MessageScrollerViewport.displayName = "MessageScrollerViewport"

export const MessageScrollerContent = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof PrimitiveScroller.Content>
>(({ className, children, ...props }, ref) => (
  <PrimitiveScroller.Content
    ref={ref}
    className={cn("flex flex-col gap-4 p-4 md:p-6 min-h-full justify-start", className)}
    {...props}
  >
    {children}
  </PrimitiveScroller.Content>
))
MessageScrollerContent.displayName = "MessageScrollerContent"

export const MessageScrollerItem = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof PrimitiveScroller.Item>
>(({ className, children, messageId, scrollAnchor, ...props }, ref) => (
  <PrimitiveScroller.Item
    ref={ref}
    messageId={messageId}
    scrollAnchor={scrollAnchor}
    className={cn("w-full outline-hidden", className)}
    {...props}
  >
    {children}
  </PrimitiveScroller.Item>
))
MessageScrollerItem.displayName = "MessageScrollerItem"

export const MessageScrollerButton = React.forwardRef<
  HTMLButtonElement,
  React.ComponentProps<typeof PrimitiveScroller.Button>
>(({ className, children, ...props }, ref) => {
  const scrollable = useMessageScrollerScrollable()
  if (!scrollable.end) return null

  return (
    <PrimitiveScroller.Button
      ref={ref}
      className={cn(
        "absolute bottom-20 left-1/2 -translate-x-1/2 z-20",
        "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold shadow-md",
        "bg-popover text-popover-foreground hover:bg-muted border border-border transition-all active:scale-95 duration-100",
        className
      )}
      {...props}
    >
      {children ?? (
        <>
          <span>Recent messages</span>
          <ArrowDown className="w-3.5 h-3.5" />
        </>
      )}
    </PrimitiveScroller.Button>
  )
})
MessageScrollerButton.displayName = "MessageScrollerButton"

export {
  useMessageScroller,
  useMessageScrollerScrollable,
  useMessageScrollerVisibility,
}

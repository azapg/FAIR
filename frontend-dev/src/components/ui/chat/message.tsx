import * as React from "react"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export interface MessageProps extends React.ComponentProps<"div"> {
  role?: "user" | "assistant" | "system"
}

const MessageContext = React.createContext<{ role: "user" | "assistant" | "system" }>({
  role: "assistant",
})

export const Message = React.forwardRef<HTMLDivElement, MessageProps>(
  ({ className, role = "assistant", children, ...props }, ref) => {
    return (
      <MessageContext.Provider value={{ role }}>
        <div
          ref={ref}
          className={cn(
            "flex w-full gap-3 md:gap-4 group items-start",
            role === "user" ? "self-end justify-end" : "self-start justify-start",
            className
          )}
          {...props}
        >
          {children}
        </div>
      </MessageContext.Provider>
    )
  }
)
Message.displayName = "Message"

export const MessageAvatar = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof Avatar> & { fallback?: React.ReactNode; src?: string }
>(({ className, fallback, src, ...props }, ref) => {
  const { role } = React.useContext(MessageContext)
  if (role === "user") return null // Users typically don't have left avatars in compact layouts

  return (
    <Avatar
      ref={ref}
      className={cn("w-8 h-8 md:w-9 h-9 border border-border/80 shadow-xs shrink-0", className)}
      {...props}
    >
      {src && <AvatarImage src={src} />}
      <AvatarFallback className="text-[10px] font-bold bg-muted/80 text-muted-foreground select-none">
        {fallback ?? "AI"}
      </AvatarFallback>
    </Avatar>
  )
})
MessageAvatar.displayName = "MessageAvatar"

export const MessageContent = React.forwardRef<HTMLDivElement, React.ComponentProps<"div">>(
  ({ className, children, ...props }, ref) => {
    const { role } = React.useContext(MessageContext)
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col gap-1.5 min-w-0 max-w-full",
          role === "user" ? "items-end" : "items-start",
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
MessageContent.displayName = "MessageContent"

export const MessageHeader = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<"div"> & { senderName?: string; timestamp?: string }
>(({ className, senderName, timestamp, children, ...props }, ref) => {
  const { role } = React.useContext(MessageContext)
  return (
    <div
      ref={ref}
      className={cn(
        "flex items-center gap-2 text-xs text-muted-foreground mb-1 select-none font-medium",
        role === "user" ? "flex-row-reverse" : "flex-row",
        className
      )}
      {...props}
    >
      {senderName && <span className="font-bold text-foreground/80">{senderName}</span>}
      {timestamp && <span>{timestamp}</span>}
      {children}
    </div>
  )
})
MessageHeader.displayName = "MessageHeader"

export const MessageFooter = React.forwardRef<HTMLDivElement, React.ComponentProps<"div">>(
  ({ className, children, ...props }, ref) => {
    const { role } = React.useContext(MessageContext)
    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center gap-1.5 mt-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus-within:opacity-100 transition-opacity duration-150 text-muted-foreground/80 select-none",
          role === "user" ? "justify-end mr-1" : "justify-start ml-1",
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
MessageFooter.displayName = "MessageFooter"

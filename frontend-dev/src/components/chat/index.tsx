import * as React from "react"
import { cn } from "@/lib/utils"
import { useIsMobile } from "@/hooks/use-mobile"
import { ChevronDown, ChevronRight, X, Plus, ArrowUp, Copy, ThumbsUp, ThumbsDown, RotateCcw, Pencil, Code, Paperclip } from "lucide-react"
import {
    Drawer,
    DrawerContent,
    DrawerHeader,
    DrawerTitle,
    DrawerClose,
} from "@/components/ui/drawer"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChainOfThought, ChainOfThoughtHeader, ChainOfThoughtContent, ChainOfThoughtStep } from "@/components/ai-elements/chain-of-thought"

export { ChainOfThoughtStep }

export function Chat({ className, children, ...props }: React.ComponentProps<"div">) {
    return (
        <div className={cn("flex w-full h-full overflow-hidden bg-background", className)} {...props}>
            {children}
        </div>
    )
}

export function Conversation({ className, children, ...props }: React.ComponentProps<"div">) {
    return (
        <div className={cn("flex-1 flex flex-col h-full min-w-0 bg-background relative", className)} {...props}>
            <ScrollArea className="flex-1 w-full relative h-full">
                <div className="mx-auto max-w-4xl px-4 md:px-8 lg:px-12 py-6 pb-48 space-y-8 flex flex-col min-h-full">
                    {children}
                </div>
            </ScrollArea>
        </div>
    )
}

export function Message({
    role = "user",
    className,
    children,
    timestamp = "Just now",
    ...props
}: React.ComponentProps<"div"> & { role?: "user" | "assistant", timestamp?: string }) {
    if (role === "user") {
        return (
            <div className={cn("self-end max-w-[85%] sm:max-w-[75%] group", className)} {...props}>
                <div className="bg-muted text-foreground px-5 py-3.5 rounded-3xl rounded-tr-md shadow-sm">
                    {children}
                </div>
                <div className="flex items-center justify-end gap-1 mt-2 mx-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity text-muted-foreground">
                    <span className="text-xs font-medium mr-2">{timestamp}</span>
                    <button className="p-1 hover:bg-muted hover:text-foreground rounded transition-colors"><RotateCcw className="w-3.5 h-3.5" /></button>
                    <button className="p-1 hover:bg-muted hover:text-foreground rounded transition-colors"><Pencil className="w-3.5 h-3.5" /></button>
                    <button className="p-1 hover:bg-muted hover:text-foreground rounded transition-colors"><Copy className="w-3.5 h-3.5" /></button>
                </div>
            </div>
        )
    }

    return (
        <div className={cn("self-start w-full", className)} {...props}>
            <div className="text-foreground leading-relaxed">
                {children}
            </div>
            <div className="flex items-center justify-start gap-1 mt-3 -ml-1.5 text-muted-foreground/80">
                <button className="p-1.5 hover:bg-muted hover:text-foreground rounded transition-colors"><Copy className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-muted hover:text-foreground rounded transition-colors"><ThumbsUp className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-muted hover:text-foreground rounded transition-colors"><ThumbsDown className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-muted hover:text-foreground rounded transition-colors"><RotateCcw className="w-4 h-4" /></button>
            </div>
        </div>
    )
}

export function Reasoning({
    summary = "Show full reasoning",
    className,
    children,
    ...props
}: React.ComponentProps<typeof ChainOfThought> & { summary?: React.ReactNode }) {
    return (
        <div className={cn("flex flex-col items-start justify-center my-1 w-full pl-0 sm:pl-[2px]", className)}>
            <ChainOfThought className="w-full max-w-2xl" {...props}>
                <ChainOfThoughtHeader>
                    {summary}
                </ChainOfThoughtHeader>
                <ChainOfThoughtContent>
                    {children}
                </ChainOfThoughtContent>
            </ChainOfThought>
        </div>
    )
}

export function Widget({
    icon,
    title,
    className,
    children,
    ...props
}: Omit<React.ComponentProps<"div">, "title"> & { icon?: React.ReactNode, title?: React.ReactNode }) {
    return (
        <div className={cn("bg-transparent border border-muted-foreground/20 rounded-full shadow-sm my-3 flex items-center gap-3 px-4 py-2 max-w-fit mx-auto sm:mx-0", className)} {...props}>
            {icon && <div className="text-muted-foreground shrink-0">{icon}</div>}
            <div className="text-sm font-medium text-foreground truncate">{title}</div>
            {children}
        </div>
    )
}

export function ChatInputContainer({ className, children, ...props }: React.ComponentProps<"div">) {
    return (
        <div className={cn("absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-background via-background to-transparent flex justify-center pb-6 z-10", className)} {...props}>
            <div className="w-full max-w-3xl">
                <div className="bg-card shadow-lg rounded-[2rem] p-2 flex flex-col gap-2 relative ring-1 ring-border/50">
                    {children}
                </div>
            </div>
        </div>
    )
}

export function ChatInput({ className, ...props }: React.ComponentProps<"textarea">) {
    return (
        <textarea
            className={cn(
                "w-full bg-transparent border-none px-4 py-2 mt-1 outline-none resize-none disabled:cursor-not-allowed disabled:opacity-50 min-h-[44px] max-h-[200px] text-[15px] text-foreground placeholder:text-muted-foreground",
                className
            )}
            placeholder="Ask a follow up question..."
            rows={1}
            {...props}
        />
    )
}

export function ChatInputActions({ className, children }: React.ComponentProps<"div">) {
    return (
        <div className={cn("flex items-center justify-between px-2 pb-1 pt-1", className)}>
            {children}
        </div>
    )
}

export function Canva({
    isOpen,
    onClose,
    title = "Research Canva",
    className,
    children,
    ...props
}: Omit<React.ComponentProps<"div">, "title"> & { isOpen?: boolean, onClose?: () => void, title?: React.ReactNode }) {
    const isMobile = useIsMobile();

    if (!isOpen) return null;

    if (isMobile) {
        return (
            <Drawer open={isOpen} onOpenChange={(open) => !open && onClose?.()}>
                <DrawerContent className="h-[90vh] flex flex-col items-stretch">
                    <DrawerHeader className="border-b text-left flex justify-between items-center px-4 py-3 shrink-0 bg-background">
                        <DrawerTitle className="text-sm font-medium flex-1 overflow-hidden" asChild>
                            <div className="truncate pr-4">{title}</div>
                        </DrawerTitle>
                        <DrawerClose asChild>
                            <button className="p-1.5 -mr-1.5 text-muted-foreground hover:bg-muted rounded-md shrink-0 transition-colors"><X className="w-4 h-4" /></button>
                        </DrawerClose>
                    </DrawerHeader>
                    <ScrollArea className="flex-1 w-full bg-muted/10 relative h-full">
                        <div className="p-4 h-full pb-8">{children}</div>
                    </ScrollArea>
                </DrawerContent>
            </Drawer>
        )
    }

    return (
        <div className={cn("w-full md:w-[450px] lg:w-[50vw] xl:w-[600px] border-l bg-card flex flex-col h-full shrink-0 shadow-[-10px_0_15px_-3px_rgba(0,0,0,0.02)] z-10 animate-in slide-in-from-right-8 duration-300 relative", className)} {...props}>
            <div className="flex items-center justify-between px-4 py-3 border-b shrink-0 bg-background/95 backdrop-blur z-20">
                <div className="flex items-center gap-2 font-medium text-sm text-foreground flex-1 pr-4">
                    {title}
                </div>
                <button onClick={onClose} className="p-1.5 hover:bg-muted rounded-md text-muted-foreground transition-colors shrink-0 outline-none focus:ring-2 focus:ring-ring">
                    <X className="w-4 h-4" />
                </button>
            </div>
            <ScrollArea className="flex-1 w-full bg-muted/5 relative h-full">
                <div className="h-full">{children}</div>
            </ScrollArea>
        </div>
    )
}

export function CanvaTriggerCard({
    icon,
    title,
    type,
    actionText = "Open",
    onClick,
    className,
    ...props
}: React.ComponentProps<"div"> & { icon?: React.ReactNode, title: string, type: string, actionText?: string, onClick?: () => void }) {
    return (
        <div
            onClick={onClick}
            className={cn("mt-4 mb-2 flex items-center justify-between p-3.5 sm:p-4 border border-border/80 rounded-xl bg-transparent hover:bg-muted/30 transition-colors cursor-pointer w-full max-w-2xl group/canva", className)}
            {...props}
        >
            <div className="flex items-center gap-4">
                <div className="w-12 h-14 sm:h-16 flex items-center justify-center bg-muted/40 rounded-lg text-muted-foreground border border-border/50 shrink-0">
                    {icon ?? <Code className="w-5 h-5 opacity-70" />}
                </div>
                <div>
                    <h4 className="font-semibold text-foreground text-[15px] leading-tight mb-1.5">{title}</h4>
                    <p className="text-muted-foreground text-[13px] font-medium tracking-wide">{type}</p>
                </div>
            </div>
            <button className="px-4 py-1.5 h-fit bg-transparent group-hover/canva:bg-background rounded-lg border border-border text-[13px] font-semibold transition-colors focus:ring-2 focus:ring-ring outline-none hover:bg-muted">
                {actionText}
            </button>
        </div>
    )
}

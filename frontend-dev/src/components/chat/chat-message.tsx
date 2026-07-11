import * as React from "react"
import { cn } from "@/lib/utils"
import { MessageScrollerItem } from "@/components/ui/chat/message-scroller"
import { Message as UIMessage, MessageContent, MessageFooter } from "@/components/ui/message"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { RepeatIcon, VolumeHighIcon } from "hugeicons-react"
import { Attachment, AttachmentMedia, AttachmentContent, AttachmentTitle, AttachmentDescription, AttachmentActions, AttachmentAction } from "@/components/ui/attachment"
import { Task, TaskTrigger, TaskContent, TaskItem, TaskItemFile } from "@/components/ai-elements/task"
import { Persona } from "@/components/ai-elements/persona"
import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardTrigger,
  InlineCitationCardBody,
} from "@/components/ai-elements/inline-citation"
import { Code, FileText, FileCode2, Terminal, Pencil, ChevronRight, DownloadIcon, RotateCcw, BookIcon, CopyIcon, ThumbsUpIcon, ThumbsDownIcon, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Message, ChatEventBlock } from "@/store/chat-store"
import { getRandomProcessingPhrase } from "@/lib/processing-phrases"

// Maps tool name strings to specific Lucide tool icons
const getToolIcon = (toolName: string) => {
  if (toolName.includes("read_file") || toolName.includes("list_dir")) {
    return FileText
  }
  if (toolName.includes("write_file") || toolName.includes("replace_file_content")) {
    return Pencil
  }
  if (toolName.includes("run_command")) {
    return Terminal
  }
  return Code
}

// Parser function to format tool execution steps into pretty blocks
const renderToolCall = (toolName: string, args: any, isRunning?: boolean) => {
  const isFileOp = toolName.includes("file") || toolName.includes("dir")
  
  if (isFileOp && args?.path) {
    const action = toolName.includes("read") || toolName.includes("list") ? "Reading" : "Writing"
    const filename = args.path.split("/").pop() || args.path
    const isCode = /\.(tsx|ts|js|jsx|json|py|rs|go)$/.test(filename)
    const FileIcon = isCode ? FileCode2 : FileText

    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", isRunning ? "animate-pulse opacity-80 text-muted-foreground" : "text-muted-foreground/80")}>
        {action}
        <TaskItemFile className="scale-95 py-0 px-1.5 h-5 flex items-center gap-1 bg-muted/60 border border-border/40 text-foreground">
          <FileIcon className="size-3 text-muted-foreground/70" />
          <span>{filename}</span>
        </TaskItemFile>
      </span>
    )
  }

  if (toolName === "run_command" && args?.command) {
    const command = args.command
    const displayCommand = command.length > 50 ? command.substring(0, 50) + "..." : command
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", isRunning ? "animate-pulse opacity-80 text-muted-foreground" : "text-muted-foreground/80")}>
        Running
        <code className="bg-muted px-1.5 py-0.5 rounded border border-border/30 font-mono text-[11px] text-muted-foreground/90 select-all">
          {displayCommand}
        </code>
      </span>
    )
  }

  return <span className={cn("text-xs font-medium", isRunning ? "animate-pulse opacity-80 text-muted-foreground" : "text-muted-foreground/80")}>{toolName}</span>
}

interface ChatMessageProps {
  message: Message
  isUser: boolean
  userRole: "simplified" | "complete"
  isTaskOpen: boolean
  onTaskOpenChange: (open: boolean) => void
  onOpenSources: () => void
  taskTimer: { elapsed: number; completed: boolean }
  personaLoaded: boolean
  onPersonaLoad: () => void
  onOpenCanvas: (content: any) => void
  onResolveInterrupt: (messageId: string, optionLabel: string) => void
  isCompletedResponse?: boolean
  hideActionsDefault?: boolean
}

export function ChatMessage({
  message,
  isUser,
  userRole,
  isTaskOpen,
  onTaskOpenChange,
  onOpenSources,
  taskTimer,
  personaLoaded,
  onPersonaLoad,
  onOpenCanvas,
  onResolveInterrupt,
  isCompletedResponse,
  hideActionsDefault
}: ChatMessageProps) {
  
  const renderContentText = (content: string, sources?: any[]) => {
    const regex = /\[(\d+)\]/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match

    const parseFormatting = (segment: string, keyPrefix: string) => {
      const codeParts = segment.split(/`([^`]+)`/g)
      return codeParts.map((part, index) => {
        if (index % 2 === 1) {
          return (
            <code key={`${keyPrefix}-code-${index}`} className="px-1.5 py-0.5 rounded bg-muted font-mono text-[13px] font-semibold text-primary/95 border border-border/40 select-all">
              {part}
            </code>
          )
        }
        const boldParts = part.split(/\*\*([^*]+)\*\*/g)
        return boldParts.map((subPart, subIndex) => {
          if (subIndex % 2 === 1) {
            return (
              <strong key={`${keyPrefix}-bold-${index}-${subIndex}`} className="font-bold text-foreground">
                {subPart}
              </strong>
            )
          }
          return subPart
        })
      })
    }

    let partCount = 0
    while ((match = regex.exec(content)) !== null) {
      const matchIndex = match.index
      const citationIndex = parseInt(match[1], 10)

      if (matchIndex > lastIndex) {
        parts.push(
          ...parseFormatting(content.substring(lastIndex, matchIndex), `p-${partCount}`)
        )
        partCount++
      }

      const source = sources?.find((s) => s.index === citationIndex)
      if (source) {
        parts.push(
          <InlineCitation key={`cit-${matchIndex}`}>
            <InlineCitationCard>
              <InlineCitationCardTrigger sources={[source.url ?? ""]} className="scale-90 select-none cursor-pointer" />
              <InlineCitationCardBody>
                <div className="p-4 space-y-1.5 text-xs select-none">
                  <div className="flex items-center gap-1.5 justify-between border-b pb-1 mb-1">
                    <span className="font-bold text-foreground truncate">{source.title}</span>
                    <span className="font-mono font-bold bg-muted px-1.5 py-0.2 rounded border text-[9px] text-muted-foreground shrink-0">
                      [{source.index}]
                    </span>
                  </div>
                  {source.snippet && <p className="text-[10px] text-muted-foreground leading-normal">{source.snippet}</p>}
                </div>
              </InlineCitationCardBody>
            </InlineCitationCard>
          </InlineCitation>
        )
      } else {
        parts.push(`[${citationIndex}]`)
      }
      lastIndex = regex.lastIndex
    }

    if (lastIndex < content.length) {
      parts.push(...parseFormatting(content.substring(lastIndex), `p-${partCount}`))
    }

    return <div className="whitespace-pre-wrap leading-relaxed">{parts}</div>
  }

  // Filter out text events to render only tools/thoughts/artifacts in the wrapper
  const nonTextEvents = message.events?.filter(e => e.type !== "text") || []
  const hasWorkingWrapper = nonTextEvents.length > 0

  return (
    <MessageScrollerItem messageId={message.id} scrollAnchor={isUser}>
      <UIMessage align={isUser ? "end" : "start"}>
        <MessageContent className={cn(!isUser && "w-full max-w-2xl")}>

          {hasWorkingWrapper && (
            <div className="mt-1 -mb-1 w-full select-none max-w-none z-10 relative">
              {(() => {
                const currentPhrase = React.useMemo(() => {
                  if (taskTimer.completed) return "Worked for"
                  return getRandomProcessingPhrase(taskTimer.elapsed)
                }, [Math.floor(taskTimer.elapsed / 3), taskTimer.completed])

                const formatTime = (elapsed: number, isCompleted: boolean) => {
                  const m = Math.floor(elapsed / 60);
                  const s = elapsed % 60;
                  const timeStr = m > 0 ? `${m}m ${s}s` : `${s}s`;
                  return isCompleted ? `Worked for ${timeStr}` : `${currentPhrase}... (${timeStr})`;
                };
                const triggerTitle = formatTime(taskTimer.elapsed, taskTimer.completed)

                // Dynamic persona state
                const personaState = taskTimer.completed 
                  ? "asleep" 
                  : (nonTextEvents.some(e => e.type === "tool_call" && e.status === "running") ? "thinking" : "idle")

                return (
                  <Task open={isTaskOpen} onOpenChange={onTaskOpenChange}>
                    <TaskTrigger title={triggerTitle}>
                      <div className="flex w-full cursor-pointer items-center text-sm font-semibold group/task hover:bg-muted/30 px-3 py-1.5 rounded-lg -mx-3 transition-all duration-200">
                        <div className={cn(
                          "transition-all duration-300 overflow-hidden flex items-center shrink-0",
                          taskTimer.completed || !personaLoaded ? "w-0 opacity-0 mr-0" : "w-6 opacity-100 mr-2"
                        )}>
                          <Persona className="w-6 h-6 shrink-0" state={personaState} variant="opal" onLoad={onPersonaLoad} />
                        </div>
                        <p className={cn("text-xs font-semibold transition-colors duration-200", !taskTimer.completed ? "shimmer text-muted-foreground" : "text-muted-foreground")}>
                          {triggerTitle}
                        </p>
                        <ChevronRight className="size-3.5 transition-transform group-data-[state=open]:rotate-90 text-muted-foreground/70 ml-2" />
                      </div>
                    </TaskTrigger>
                    
                    <TaskContent>
                      <div className="flex flex-col gap-2.5 py-1">
                        {nonTextEvents.map((ev, idx) => {
                          if (ev.type === "thought") {
                            return (
                              <div key={idx} className="text-[13px] text-muted-foreground/80 italic leading-relaxed py-0.5">
                                {ev.content}
                              </div>
                            )
                          }
                          
                          if (ev.type === "artifact_update") {
                            return (
                              <div key={idx} className="flex items-center gap-2 text-[11px] font-medium bg-muted/30 border border-border/50 rounded-md px-2 py-1 w-fit my-0.5 text-muted-foreground">
                                <FileCode2 className="w-3.5 h-3.5" />
                                <span>{ev.action === "create" ? "Created" : "Edited"} {ev.artifactName}</span>
                                {ev.diff && (
                                  <span className="flex items-center gap-1.5 font-mono">
                                    <span className="text-emerald-500">+{ev.diff.added}</span>
                                    <span className="text-red-500">-{ev.diff.removed}</span>
                                  </span>
                                )}
                              </div>
                            )
                          }

                          if (ev.type === "tool_call") {
                            const ToolIcon = getToolIcon(ev.toolName)
                            const isRunning = ev.status === "running" && !taskTimer.completed
                            return (
                              <div key={idx} className="flex items-center gap-2.5 py-0.5 select-none">
                                <ToolIcon className={cn("w-4 h-4 shrink-0 text-muted-foreground/60", isRunning && "animate-pulse")} />
                                <TaskItem className="flex-1 flex items-center justify-between">
                                  {renderToolCall(ev.toolName, ev.args, isRunning)}
                                </TaskItem>
                              </div>
                            )
                          }
                        })}
                      </div>
                    </TaskContent>
                  </Task>
                )
              })()}
            </div>
          )}

          {message.attachments && message.attachments.length > 0 && (
            <div className={cn("flex flex-col gap-1.5 mb-0 select-none w-full max-w-xl", isUser && "ml-auto items-end")}>
              {message.attachments.map((file, fIdx) => (
                <Attachment key={fIdx} orientation={file.isImage ? "vertical" : "horizontal"}>
                  <AttachmentMedia variant={file.isImage ? "image" : "icon"}>
                    {file.isImage ? <img src={file.src} alt={file.name} /> : <FileText className="w-4 h-4 text-muted-foreground" />}
                  </AttachmentMedia>
                  <AttachmentContent>
                    <AttachmentTitle>{file.name}</AttachmentTitle>
                    <AttachmentDescription>{file.type} · {file.size}</AttachmentDescription>
                  </AttachmentContent>
                </Attachment>
              ))}
            </div>
          )}

          {(() => {
            const canvasWidget = message.canvasContent && (
              <div
                onClick={() => onOpenCanvas(message.canvasContent)}
                className={cn(
                  "mt-1.5 flex items-center justify-between p-3.5 border border-border/80 rounded-xl bg-card hover:bg-muted/30 transition-colors cursor-pointer w-full max-w-md group/canva select-none",
                  isUser && "ml-auto"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 flex items-center justify-center bg-muted/40 rounded-lg text-muted-foreground border border-border/50 shrink-0">
                    <Code className="w-4 h-4 opacity-70" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground text-xs leading-tight mb-1">{message.canvasContent.title}</h4>
                    <p className="text-muted-foreground text-[10px] uppercase font-bold tracking-wider">{message.canvasContent.type}</p>
                  </div>
                </div>
                <Button variant="outline" size="sm" className="h-8 gap-1 text-[11px] font-semibold bg-background group-hover/canva:bg-muted transition-colors">
                  Open Canvas <ExternalLink className="w-3 h-3" />
                </Button>
              </div>
            )

            return isUser ? (
              <div className="flex flex-col">
                <Bubble variant="muted" className="ml-auto">
                  <BubbleContent className="whitespace-pre-wrap">{message.content}</BubbleContent>
                </Bubble>
                {canvasWidget}
              </div>
            ) : (
              <div className="w-full">
                {message.content && (
                  <div className="w-full text-foreground/90 leading-relaxed text-[15px] select-text pt-0.5 pb-0">
                    {renderContentText(message.content, message.sources)}
                  </div>
                )}
                {canvasWidget}
                {taskTimer.completed && isCompletedResponse !== false && (
                  <MessageFooter className={cn("mt-0 gap-0 px-0", hideActionsDefault && "opacity-0 group-hover/message:opacity-100 transition-opacity duration-200")}>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted"><CopyIcon className="w-4 h-4" /></Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted"><ThumbsUpIcon className="w-4 h-4" /></Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted"><ThumbsDownIcon className="w-4 h-4" /></Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted"><RepeatIcon className="w-4 h-4" /></Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted"><VolumeHighIcon className="w-4 h-4" /></Button>
                    {message.sources && message.sources.length > 0 && (
                      <Button variant="ghost" size="sm" className="h-8 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted px-2 ml-1" onClick={onOpenSources}>
                        <BookIcon className="w-3.5 h-3.5 mr-1.5" /> Sources
                      </Button>
                    )}
                  </MessageFooter>
                )}
              </div>
            )
          })()}
        </MessageContent>
      </UIMessage>
    </MessageScrollerItem>
  )
}

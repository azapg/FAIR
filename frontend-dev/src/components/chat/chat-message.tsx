import * as React from "react"
import { cn } from "@/lib/utils"
import { MessageScrollerItem } from "@/components/ui/chat/message-scroller"
import { Message, MessageContent, MessageFooter } from "@/components/ui/message"
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
import { Code, FileText, FileCode2, Terminal, Pencil, ChevronRight, Loader2, Hand, Check, ExternalLink, CopyIcon, ThumbsUpIcon, ThumbsDownIcon, DownloadIcon, RotateCcw, BookIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MockMessage } from "@/app/chat/mock-chat-scenarios"

// Maps task title strings to specific Lucide tool icons without colors
const getToolIcon = (taskTitle: string) => {
  if (taskTitle.startsWith("read_file")) {
    return FileText
  }
  if (taskTitle.startsWith("write_file")) {
    return Pencil
  }
  if (taskTitle.startsWith("exec")) {
    return Terminal
  }
  return Code
}

// Parser function to format tool execution steps into pretty, reader-friendly blocks with file icons
const renderTaskItem = (taskTitle: string, isRunning?: boolean) => {
  const fileMatch = taskTitle.match(/^(read_file|write_file)\("([^"]+)"\)$/)
  if (fileMatch) {
    const [_, tool, filepath] = fileMatch
    const action = tool === "read_file" ? "Reading file" : "Writing file"
    const filename = filepath.split("/").pop() || filepath
    
    // Choose icon based on file extension
    const isCode = /\.(tsx|ts|js|jsx|json)$/.test(filepath)
    const FileIcon = isCode ? FileCode2 : FileText

    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", isRunning ? "shimmer text-muted-foreground" : "text-muted-foreground/80")}>
        {action}
        <TaskItemFile className="scale-95 py-0 px-1.5 h-5 flex items-center gap-1 bg-muted/60 border border-border/40 text-foreground">
          <FileIcon className="size-3 text-muted-foreground/70" />
          <span>{filename}</span>
        </TaskItemFile>
      </span>
    )
  }

  const execMatch = taskTitle.match(/^exec\("([^"]+)"\)$/)
  if (execMatch) {
    const [_, command] = execMatch
    const displayCommand = command.length > 50 ? command.substring(0, 50) + "..." : command
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", isRunning ? "shimmer text-muted-foreground" : "text-muted-foreground/80")}>
        Running command
        <code className="bg-muted px-1.5 py-0.5 rounded border border-border/30 font-mono text-[11px] text-muted-foreground/90 select-all">
          {displayCommand}
        </code>
      </span>
    )
  }

  return <span className={cn("text-xs font-medium", isRunning ? "shimmer text-muted-foreground" : "text-muted-foreground/80")}>{taskTitle}</span>
}

interface ChatMessageProps {
  message: MockMessage
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
  isCompletedResponse
}: ChatMessageProps) {
  
  // Helper function to render text content and swap out [1], [2] with InlineCitation components, plus parse basic markdown
  const renderContentText = (content: string, sources?: any[]) => {
    const regex = /\[(\d+)\]/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match

    // Helper to parse formatting (bold and code) within a text segment
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
                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[10px] text-primary hover:underline block truncate mt-1.5"
                    >
                      {source.url}
                    </a>
                  )}
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
      parts.push(
        ...parseFormatting(content.substring(lastIndex), `p-${partCount}`)
      )
    }

    return <div className="whitespace-pre-wrap leading-relaxed">{parts}</div>
  }

  return (
    <MessageScrollerItem
      messageId={message.id}
      scrollAnchor={isUser}
    >
      <Message align={isUser ? "end" : "start"}>
        <MessageContent className={cn(!isUser && "w-full max-w-2xl")}>

          {/* Collapsible Task with auto-collapse states and timer */}
          {message.tasks && message.tasks.length > 0 && (
            <div className="mt-1 -mb-1 w-full select-none max-w-none z-10 relative">
              {(() => {
                const formatTime = (elapsed: number, isCompleted: boolean) => {
                  const h = Math.floor(elapsed / 3600);
                  const m = Math.floor((elapsed % 3600) / 60);
                  const s = elapsed % 60;
                  const parts = [];
                  if (h > 0) parts.push(`${h}h`);
                  if (m > 0) parts.push(`${m}m`);
                  parts.push(`${s}s`);
                  const timeStr = parts.join(" ");
                  return isCompleted ? `Worked for ${timeStr}` : `Working for ${timeStr}`;
                };
                const triggerTitle = formatTime(taskTimer.elapsed, taskTimer.completed)

                // Dynamic persona state: asleep when done, thinking when working, idle when appearing/pending
                const personaState = taskTimer.completed
                  ? "asleep"
                  : (message.tasks!.some(t => t.state === "running") ? "thinking" : "idle")

                return (
                  <Task
                    open={isTaskOpen}
                    onOpenChange={onTaskOpenChange}
                  >
                    <TaskTrigger title={triggerTitle}>
                      <div className="flex w-full cursor-pointer items-center text-sm font-semibold group/task hover:bg-muted/30 px-3 py-1.5 rounded-lg -mx-3 transition-all duration-200">
                        {/* Dynamic 1.5x animated Persona blob, fading in on ready to prevent blank shifts */}
                        <div
                          className={cn(
                            "transition-all duration-300 overflow-hidden flex items-center shrink-0",
                            taskTimer.completed || !personaLoaded ? "w-0 opacity-0 mr-0" : "w-6 opacity-100 mr-2"
                          )}
                        >
                          <Persona
                            className="w-6 h-6 shrink-0"
                            state={personaState}
                            variant="opal"
                            onLoad={onPersonaLoad}
                          />
                        </div>
                        <p className={cn("text-xs font-semibold transition-colors duration-200", !taskTimer.completed ? "shimmer text-muted-foreground" : "text-muted-foreground")}>{triggerTitle}</p>
                        <ChevronRight className="size-3.5 transition-transform group-data-[state=open]:rotate-90 text-muted-foreground/70 ml-2" />
                        
                        {/* Status pulse label rendering */}
                        {message.statusPulse && !taskTimer.completed && (
                          <span className="text-[10px] text-muted-foreground/60 font-normal italic ml-2 border-l pl-2">
                            {message.statusPulse.message}
                          </span>
                        )}
                      </div>
                    </TaskTrigger>
                    
                    <TaskContent>
                      {message.tasks!.map((task, tIdx) => {
                        const ToolIcon = getToolIcon(task.title)
                        return (
                          <div key={tIdx} className="flex items-center gap-2.5 py-1 select-none">
                            <ToolIcon className={cn(
                              "w-4 h-4 shrink-0 text-muted-foreground/85",
                              task.state === "running" && "animate-pulse"
                            )} />
                            <TaskItem className="flex-1 flex items-center justify-between">
                              {renderTaskItem(task.title, task.state === "running")}
                            </TaskItem>
                          </div>
                        )
                      })}
                    </TaskContent>
                  </Task>
                )
              })()}
            </div>
          )}

          {/* Render attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className={cn("flex flex-col gap-1.5 mb-0 select-none w-full max-w-xl", isUser && "ml-auto items-end")}>
              {message.attachments.map((file, fIdx) => (
                <Attachment key={fIdx} orientation={file.isImage ? "vertical" : "horizontal"}>
                  <AttachmentMedia variant={file.isImage ? "image" : "icon"}>
                    {file.isImage ? (
                      <img src={file.src} alt={file.name} />
                    ) : (
                      <FileText className="w-4 h-4 text-muted-foreground" />
                    )}
                  </AttachmentMedia>
                  <AttachmentContent>
                    <AttachmentTitle>{file.name}</AttachmentTitle>
                    <AttachmentDescription>{file.type} · {file.size}</AttachmentDescription>
                  </AttachmentContent>
                  <AttachmentActions>
                    <AttachmentAction
                      type="button"
                      title="Download"
                      aria-label="Download"
                      size="icon-sm"
                      variant="secondary"
                      onClick={() => alert(`Downloading: ${file.name}`)}
                    >
                      <DownloadIcon className="w-4 h-4" />
                    </AttachmentAction>
                  </AttachmentActions>
                </Attachment>
              ))}
            </div>
          )}

          {/* Content Bubble or Naked Markdown */}
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
                    <h4 className="font-semibold text-foreground text-xs leading-tight mb-1">
                      {message.canvasContent.title}
                    </h4>
                    <p className="text-muted-foreground text-[10px] uppercase font-bold tracking-wider">
                      {message.canvasContent.type}
                    </p>
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
                <MessageFooter className="mt-1 gap-0 px-0 opacity-0 group-hover/message:opacity-100 transition-opacity focus-within:opacity-100">
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Retry" title="Retry">
                    <RotateCcw className="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Edit" title="Edit">
                    <Pencil className="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Copy" title="Copy">
                    <CopyIcon className="w-3.5 h-3.5" />
                  </Button>
                </MessageFooter>
              </div>
            ) : (
              /* Naked Markdown response (no bubble) directly on the background */
              <div className="w-full">
                <div className="w-full text-foreground/90 leading-relaxed text-[15px] select-text pt-0.5 pb-1">
                  {renderContentText(message.content, message.sources)}
                </div>
                {canvasWidget}
                {taskTimer.completed && isCompletedResponse !== false && (
                  <MessageFooter className="mt-2 gap-0 px-0">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Copy" title="Copy">
                      <CopyIcon className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Good response" title="Good response">
                      <ThumbsUpIcon className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Bad response" title="Bad response">
                      <ThumbsDownIcon className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Try again" title="Try again">
                      <RepeatIcon className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted" aria-label="Listen" title="Listen">
                      <VolumeHighIcon className="w-4 h-4" />
                    </Button>
                    {message.sources && message.sources.length > 0 && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted px-2 ml-1" 
                        onClick={onOpenSources}
                      >
                        <BookIcon className="w-3.5 h-3.5 mr-1.5" />
                        Sources
                      </Button>
                    )}
                  </MessageFooter>
                )}
              </div>
            )
          })()}
        </MessageContent>
      </Message>
    </MessageScrollerItem>
  )
}

import * as React from "react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { BookIcon, X, ExternalLink, FileText, Globe } from "lucide-react"

interface Source {
  title: string
  url?: string
  snippet?: string
  index: number
  type?: "web" | "file" | "doc"
}

interface SourcesSidebarProps {
  sources: Source[]
  onClose: () => void
}

export function SourcesSidebar({ sources, onClose }: SourcesSidebarProps) {
  const titleId = React.useId()
  const closeButtonRef = React.useRef<HTMLButtonElement | null>(null)
  const previousFocusRef = React.useRef<HTMLElement | null>(null)

  React.useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    closeButtonRef.current?.focus()

    return () => {
      const previousFocus = previousFocusRef.current
      if (previousFocus?.isConnected) previousFocus.focus()
    }
  }, [])

  return (
    <aside aria-labelledby={titleId} className="w-80 border-l bg-card/40 flex flex-col h-full shrink-0 transition-all duration-300 ease-in-out">
      <div className="p-4 border-b shrink-0 flex items-center justify-between">
        <h2 id={titleId} className="text-sm font-bold text-foreground/80 tracking-wide uppercase flex items-center gap-2">
          <BookIcon className="w-4 h-4 text-primary" /> Sources
        </h2>
        <Button
          ref={closeButtonRef}
          variant="ghost"
          size="icon"
          aria-label="Close sources"
          onClick={onClose}
          className="h-7 w-7 rounded-lg hover:bg-muted cursor-pointer shrink-0"
          title="Close sources"
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </Button>
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-3">
          {sources.map((src) => {
            const Icon = src.type === "file" ? FileText : Globe
            
            return (
              <div 
                key={src.index} 
                className="flex flex-col gap-1.5 p-3 rounded-xl border bg-card text-left transition-colors hover:bg-muted/50"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-[10px] font-mono font-bold shrink-0 bg-muted px-1.5 py-0.5 rounded border border-border/40 text-muted-foreground">
                      [{src.index}]
                    </span>
                    <span className="text-sm font-semibold text-foreground truncate" title={src.title}>
                      {src.title}
                    </span>
                  </div>
                  {src.url && (
                    <a 
                      href={src.url} 
                      target="_blank" 
                      rel="noreferrer"
                      aria-label={`Open ${src.title} in a new tab`}
                      className="text-muted-foreground hover:text-primary transition-colors mt-0.5 shrink-0"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
                {src.snippet && (
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-3">
                    {src.snippet}
                  </p>
                )}
                <div className="flex items-center gap-1 mt-1 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  <Icon className="w-3 h-3" />
                  {src.type || "web"}
                </div>
              </div>
            )
          })}
        </div>
      </ScrollArea>
    </aside>
  )
}

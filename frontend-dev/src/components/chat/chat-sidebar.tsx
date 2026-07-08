import * as React from "react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Sparkles, Play, RotateCcw, Info, ChevronLeft, ChevronRight } from "lucide-react"
import { mockScenarios } from "@/app/chat/mock-chat-scenarios"

interface ChatSidebarProps {
  userRole: "simplified" | "complete"
  setUserRole: (role: "simplified" | "complete") => void
  selectedScenarioId: string
  setSelectedScenarioId: (id: string) => void
  activeScenario: any
  playbackIndex: number
  isStreaming: boolean
  hasUnresolvedElicitation: boolean
  playNextTurn: () => void
  resetSimulation: () => void
}

export function ChatSidebar({
  userRole,
  setUserRole,
  selectedScenarioId,
  setSelectedScenarioId,
  activeScenario,
  playbackIndex,
  isStreaming,
  hasUnresolvedElicitation,
  playNextTurn,
  resetSimulation
}: ChatSidebarProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(false)

  return (
    <div className={cn(
      "border-r bg-card/40 flex flex-col h-full shrink-0 transition-all duration-300 ease-in-out overflow-hidden relative",
      isCollapsed ? "w-12" : "w-80"
    )}>
      {isCollapsed ? (
        <div className="flex flex-col items-center py-4 h-full w-full gap-4 animate-in fade-in duration-200">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(false)}
            className="h-8 w-8 rounded-xl hover:bg-muted cursor-pointer"
            title="Expand Test System Panel"
          >
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </Button>
          <div className="flex-1 flex items-center justify-center">
            <span className="text-[10px] font-bold text-muted-foreground tracking-widest uppercase select-none opacity-40 [writing-mode:vertical-lr] rotate-180">
              Test System Panel
            </span>
          </div>
          <div className="mb-2">
            <Sparkles className="w-4 h-4 text-primary opacity-65" />
          </div>
        </div>
      ) : (
        <div className="flex flex-col h-full w-full animate-in fade-in duration-200">
          {/* Role Selector Dashboard Tab Panel */}
          <div className="p-4 border-b shrink-0 space-y-3.5">
            {/* Title */}
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-foreground/80 tracking-wide uppercase flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-primary" /> Test System Panel
              </h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsCollapsed(true)}
                className="h-7 w-7 rounded-lg hover:bg-muted cursor-pointer shrink-0"
                title="Collapse Test System Panel"
              >
                <ChevronLeft className="w-4 h-4 text-muted-foreground" />
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Choose scenarios to test scrolling, streaming, and canvas capabilities.
            </p>

        {/* Role Selector */}
        <div className="space-y-2 shrink-0">
          <label className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block">
            Select UI Role View
          </label>
          <div className="grid grid-cols-2 gap-1 bg-muted/60 p-0.5 rounded-xl border border-border/50 select-none">
            {(["simplified", "complete"] as const).map((role) => (
              <button
                key={role}
                onClick={() => setUserRole(role)}
                className={cn(
                  "py-1 text-[10px] font-bold rounded-lg capitalize transition-all cursor-pointer",
                  userRole === role
                    ? "bg-background text-foreground shadow-xs border border-border/25"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {role}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Scrollable Sidebar Content */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-4">
          {/* Scenario Selector */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-muted-foreground uppercase">
              Select Scenario
            </label>
            <div className="flex flex-col gap-1">
              {mockScenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  onClick={() => setSelectedScenarioId(scenario.id)}
                  className={cn(
                    "text-left px-3 py-2 rounded-xl text-xs font-semibold border transition-all flex flex-col gap-0.5 w-full",
                    selectedScenarioId === scenario.id
                      ? "bg-primary/5 border-primary/30 text-primary shadow-xs"
                      : "bg-transparent border-transparent hover:bg-muted text-muted-foreground"
                  )}
                >
                  <span className="text-foreground font-bold truncate">{scenario.title}</span>
                  <span className="text-[10px] font-normal leading-normal opacity-85 line-clamp-2">
                    {scenario.description}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Simulation Control (Fixed) */}
      <div className="p-4 border-t space-y-3 shrink-0">
        <label className="text-[11px] font-bold text-muted-foreground uppercase block">
          Simulation Control
        </label>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={playNextTurn}
            disabled={isStreaming || playbackIndex >= activeScenario.messages.length || hasUnresolvedElicitation}
            className="flex items-center gap-1 text-xs"
          >
            <Play className="w-3.5 h-3.5" /> Step Next
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => resetSimulation()}
            className="flex items-center gap-1 text-xs text-destructive hover:bg-destructive/5"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset
          </Button>
        </div>
        <div className="bg-muted/40 p-3 rounded-xl border space-y-1">
          <div className="text-[10px] text-muted-foreground flex justify-between font-semibold">
            <span>Scenario progress:</span>
            <span>
              {playbackIndex} / {activeScenario.messages.length} turns
            </span>
          </div>
          <div className="w-full bg-muted h-1 rounded-full overflow-hidden mt-1.5">
            <div
              className="bg-primary h-full transition-all duration-300"
              style={{
                width: `${(playbackIndex / activeScenario.messages.length) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>

      <div className="p-4 border-t bg-muted/20 shrink-0">
        <div className="flex items-start gap-2.5">
          <Info className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
          <div className="text-[10px] text-muted-foreground leading-normal font-medium">
            Auto-scroll keeps output pinned to the bottom. Scroll up manually to pause auto-scrolling.
          </div>
        </div>
      </div>
      </div>
      )}
    </div>
  )
}

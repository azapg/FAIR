import * as React from "react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sparkles, X } from "lucide-react"
import { DoublePendulum } from "./double-pendulum"

interface ChatCanvasProps {
  activeCanvasContent: any
  setCanvaOpen: (open: boolean) => void
}

export function ChatCanvas({
  activeCanvasContent,
  setCanvaOpen
}: ChatCanvasProps) {
  if (!activeCanvasContent) return null

  return (
    <div className="w-[45%] border-l bg-card flex flex-col h-full shrink-0 shadow-xl z-20 relative animate-in slide-in-from-right duration-300">
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0 bg-background/95 backdrop-blur">
        <div className="flex items-center gap-2 font-semibold text-xs text-foreground flex-1 pr-4 truncate uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5 text-primary" /> {activeCanvasContent.title}
        </div>
        <button
          onClick={() => setCanvaOpen(false)}
          className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors shrink-0 outline-hidden cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      
      {/* Scrollable Canva contents using shadcn's ScrollArea component */}
      <ScrollArea className="flex-1 w-full bg-muted/5">
        <div className="p-4 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b">
            <div className="text-xs text-muted-foreground font-semibold flex items-center gap-1.5">
              Type: <span className="bg-muted px-2 py-0.5 rounded-full text-foreground border text-[10px] font-bold uppercase">{activeCanvasContent.type}</span>
            </div>
          </div>

          {/* Render dynamic visualizations */}
          {activeCanvasContent.visualType === "chart" && activeCanvasContent.data && (
            <div className="bg-background border rounded-2xl p-5 shadow-xs">
              <h4 className="font-bold text-center mb-6 text-sm tracking-tight text-foreground/90">
                {activeCanvasContent.title}
              </h4>
              <div className="aspect-[1.5] w-full bg-transparent border-l border-b border-muted-foreground/30 flex flex-col pt-4 pr-16 pb-6 pl-3 relative group hover:border-muted-foreground transition-colors select-none">
                {/* Y Grid lines */}
                <div className="absolute left-0 right-16 top-[10%] border-t border-dashed border-border/40"></div>
                <div className="absolute left-0 right-16 top-[30%] border-t border-dashed border-border/40"></div>
                <div className="absolute left-0 right-16 top-[50%] border-t border-dashed border-border/40"></div>
                <div className="absolute left-0 right-16 top-[70%] border-t border-dashed border-border/40"></div>
                
                {/* Y Labels */}
                <div className="absolute -left-8 top-[10%] -translate-y-1/2 text-[9px] text-muted-foreground font-medium">9k</div>
                <div className="absolute -left-8 top-[30%] -translate-y-1/2 text-[9px] text-muted-foreground font-medium">7k</div>
                <div className="absolute -left-8 top-[50%] -translate-y-1/2 text-[9px] text-muted-foreground font-medium">5k</div>
                <div className="absolute -left-8 top-[70%] -translate-y-1/2 text-[9px] text-muted-foreground font-medium">3k</div>
                <div className="absolute -left-8 bottom-0 translate-y-1/2 text-[9px] text-muted-foreground font-medium">0</div>

                {/* X Labels */}
                <div className="absolute left-[0%] -bottom-6 -translate-x-1/2 text-[9px] text-muted-foreground font-medium">2014</div>
                <div className="absolute left-[25%] -bottom-6 -translate-x-1/2 text-[9px] text-muted-foreground font-medium">2016</div>
                <div className="absolute left-[50%] -bottom-6 -translate-x-1/2 text-[9px] text-muted-foreground font-medium">2018</div>
                <div className="absolute left-[75%] -bottom-6 -translate-x-1/2 text-[9px] text-muted-foreground font-medium">2020</div>
                <div className="absolute left-[100%] right-16 -bottom-6 -translate-x-1/2 text-[9px] text-muted-foreground font-medium">2022</div>

                {/* SVG Chart Drawing */}
                <svg className="w-full h-full overflow-visible" preserveAspectRatio="none">
                  {Object.keys(activeCanvasContent.data.series || {}).map((region, idx) => {
                    const values = activeCanvasContent.data.series[region]
                    const colors = [
                      "stroke-blue-500",
                      "stroke-orange-500",
                      "stroke-pink-500",
                      "stroke-purple-500",
                      "stroke-green-500",
                      "stroke-cyan-500"
                    ]
                    const colorClass = colors[idx % colors.length]
                    
                    const points = values.map((val: number, i: number) => {
                      const x = (i / (values.length - 1)) * 100
                      const y = 100 - val
                      return `${x}%,${y}%`
                    }).join(" ")

                    return (
                      <polyline
                        key={region}
                        points={points}
                        fill="none"
                        strokeWidth="2.5"
                        className={cn(colorClass, "transition-all duration-300")}
                      />
                    )
                  })}
                </svg>

                {/* Legend */}
                <div className="absolute -right-2 top-0 w-16 text-[9px] space-y-1.5 flex flex-col justify-start items-start text-muted-foreground font-semibold p-1">
                  <span className="font-bold text-foreground text-[10px] mb-1">Region</span>
                  <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-blue-500"></div>AFR</div>
                  <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-orange-500"></div>AMR</div>
                  <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-pink-500"></div>EMR</div>
                  <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-purple-500"></div>EUR</div>
                  <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-green-500"></div>SEA</div>
                  <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-cyan-500"></div>WPR</div>
                </div>
              </div>
            </div>
          )}

          {/* Render Pendulum Physics Simulation */}
          {activeCanvasContent.visualType === "simulation" && (
            <div className="bg-background border rounded-2xl p-4 shadow-xs">
              <h4 className="font-bold text-center mb-3 text-xs tracking-tight text-foreground/80 flex items-center justify-center gap-1.5">
                Double Pendulum Chaos Engine
              </h4>
              <DoublePendulum />
            </div>
          )}

          {/* Code block rendering */}
          {activeCanvasContent.code && (
            <div className="bg-muted p-4 rounded-xl border font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed select-text shadow-inner">
              <code className="text-foreground/90">{activeCanvasContent.code}</code>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

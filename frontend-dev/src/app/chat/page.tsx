import * as React from "react"
import { cn } from "@/lib/utils"
import {
  MessageScroller,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
  MessageScrollerProvider,
} from "@/components/ui/chat/message-scroller"
import { Persona } from "@/components/ai-elements/persona"
import { ChevronDown, Check, Pencil, X, ChevronRight, CheckCircle, MessageSquare, LineChart, Compass, BarChart } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu"

import { useScenarioPlayback } from "@/hooks/use-scenario-playback"
import { useChatStore } from "@/store/chat-store"
import { ChatSidebar } from "@/components/chat/chat-sidebar"
import { ChatInput } from "@/components/chat/chat-input"
import { ChatMessage } from "@/components/chat/chat-message"
import { ChatCanvas } from "@/components/chat/chat-canvas"
import { SourcesSidebar } from "@/components/chat/sources-sidebar"
import { ElicitationPanel } from "@/components/chat/elicitation-panel"

const GREETINGS = [
  "Any new ideas to explore?",
  "How can I help, Allan?",
  "What are we building today, Allan?",
  "Let's analyze some results, Allan.",
  "What simulation are we designing today, Allan?"
]

const WORK_IDEAS = [
  {
    id: "grade",
    label: "Grade",
    icon: CheckCircle,
    prompts: [
      "Grade this batch against my rubric",
      "Flag submissions where the AI grader was uncertain",
      "Compare two submissions side by side",
      "Re-grade this submission with updated criteria",
      "Show me grading inconsistencies across sections"
    ]
  },
  {
    id: "design",
    label: "Design",
    icon: Pencil,
    prompts: [
      "Build a rubric from this assignment description",
      "Generate a rubric from these example solutions",
      "Turn my old grading comments into a reusable rubric",
      "Create variations of this problem set",
      "Draft an assignment that targets [knowledge component]"
    ]
  },
  {
    id: "feedback",
    label: "Feedback",
    icon: MessageSquare,
    prompts: [
      "Write personalized feedback for this submission",
      "Summarize common mistakes across the class",
      "Translate this feedback into something less harsh",
      "Draft a message to a student who's been struggling",
      "Generate feedback templates for recurring errors"
    ]
  },
  {
    id: "insights",
    label: "Insights",
    icon: LineChart,
    prompts: [
      "Show me which students are clustering at the bottom",
      "Which questions had the most inconsistent grading?",
      "Where does the AI grader disagree with me most?",
      "Which knowledge components is my class weakest in?",
      "Show grade distribution trends over the semester"
    ]
  },
  {
    id: "explore",
    label: "Explore",
    icon: Compass,
    prompts: [
      "What patterns show up in failed submissions this term?",
      "Compare this semester's performance to last semester's",
      "Find outlier students who don't fit the usual trend",
      "What rubric criteria get debated or overridden most?",
      "Surface questions students keep getting wrong in similar ways"
    ]
  },
  {
    id: "visualize",
    label: "Visualize",
    icon: BarChart,
    prompts: [
      "Chart grade distribution for this assignment",
      "Show a heatmap of errors by knowledge component",
      "Visualize how this student's performance changed over time",
      "Plot AI grader confidence against final grade",
      "Map the class's strengths and weaknesses by topic"
    ]
  }
]

export default function ChatPage() {
  return (
    <MessageScrollerProvider autoScroll>
      <ChatDashboard />
    </MessageScrollerProvider>
  )
}

function ChatDashboard() {
  // Global Store State
  const store = useChatStore()
  
  // Local UI State
  const [inputPlaceholder, setInputPlaceholder] = React.useState("Write a message...")
  const [hoveredPrompt, setHoveredPrompt] = React.useState<string | null>(null)
  const [activeIdeaId, setActiveIdeaId] = React.useState<string | null>(null)
  const [taskTimers, setTaskTimers] = React.useState<Record<string, { elapsed: number; completed: boolean }>>({})
  
  // Scenario Playback Orchestrator (Side-effects mostly)
  const {
    userRole,
    setUserRole,
    selectedScenarioId,
    setSelectedScenarioId,
    activeScenario,
    isStreaming,
    playbackIndex,
    openStates,
    setOpenStates,
    personaLoaded,
    setPersonaLoaded,
    resetSimulation,
    playNextTurn,
    handleResolveElicitation,
    handleSend,
    simulateMessage
  } = useScenarioPlayback()

  const greeting = React.useMemo(() => {
    return GREETINGS[Math.floor(Math.random() * GREETINGS.length)]
  }, [selectedScenarioId])

  const isCanvasVisible = store.isCanvasOpen && store.activeCanvasContent
  const lastMsg = store.messages[store.messages.length - 1]
  const isThinking = store.agentState === "thinking"
  
  const hasUnresolvedElicitation = store.agentState === "waiting_for_user"
  const activeElicitationMessage = store.messages.find(
    (msg) => msg.elicitation && !msg.elicitation.resolved
  )
  
  const activeSourcesMessage = React.useMemo(() => {
    return store.messages.find(m => m.id === store.activeSourcesMessageId)
  }, [store.messages, store.activeSourcesMessageId])

  const activeIdea = WORK_IDEAS.find(i => i.id === activeIdeaId)

  // Track task timers safely whenever streaming starts/stops
  React.useEffect(() => {
    if (store.streamingMessageId && isStreaming) {
      const id = store.streamingMessageId
      setTaskTimers(prev => ({ ...prev, [id]: { elapsed: 0, completed: false } }))
      const timer = setInterval(() => {
        const currentMsg = useChatStore.getState().messages.find(m => m.id === id)
        const hasStartedReplying = (currentMsg?.content?.length || 0) > 0

        setTaskTimers(prev => {
          const current = prev[id]
          if (!current || current.completed || hasStartedReplying) return prev
          return { ...prev, [id]: { ...current, elapsed: current.elapsed + 1 } }
        })
      }, 1000)
      return () => clearInterval(timer)
    } else if (store.streamingMessageId) {
      setTaskTimers(prev => ({
        ...prev,
        [store.streamingMessageId!]: { 
          elapsed: prev[store.streamingMessageId!]?.elapsed || 1, 
          completed: true 
        }
      }))
    }
  }, [store.streamingMessageId, isStreaming])

  return (
    <div className="h-screen w-full flex bg-background overflow-hidden border-t">
      {/* Sidebar Controls */}
      <ChatSidebar
        userRole={userRole}
        setUserRole={setUserRole}
        selectedScenarioId={selectedScenarioId}
        setSelectedScenarioId={setSelectedScenarioId}
        activeScenario={activeScenario}
        playbackIndex={playbackIndex}
        isStreaming={isStreaming}
        hasUnresolvedElicitation={hasUnresolvedElicitation}
        playNextTurn={playNextTurn}
        resetSimulation={resetSimulation}
        simulateMessage={simulateMessage}
      />


      <div className="flex-grow flex overflow-hidden relative h-full">
        {/* Left/Conversation Panel containing Top Header and Message History */}
        <div className={cn(
          "flex flex-col h-full overflow-hidden transition-all duration-300 ease-in-out",
          isCanvasVisible ? "w-[55%] shrink-0" : "w-full flex-grow"
        )}>
          {/* Top Header Bar */}
          <div className="h-14 flex items-center justify-between px-6 shrink-0 z-10 select-none">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-1.5 px-3 py-1.5 text-base font-bold text-foreground hover:bg-muted rounded-xl transition-all cursor-pointer select-none">
                  <span>{store.selectedModel === "feynman" ? "Feynman" : "Einstein"}</span>
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-72 p-2 rounded-2xl bg-card border shadow-xl z-50">
                <DropdownMenuItem onClick={() => store.setSelectedModel("feynman")} className={cn("flex flex-col items-start gap-0.5 p-3 rounded-xl cursor-pointer", store.selectedModel === "feynman" && "bg-muted")}>
                  <div className="flex items-center justify-between w-full">
                    <span className="font-bold text-sm">Feynman</span>
                    {store.selectedModel === "feynman" && <Check className="w-4 h-4 text-foreground" />}
                  </div>
                  <span className="text-[11px] text-muted-foreground">Great for everyday tasks</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => store.setSelectedModel("einstein")} className={cn("flex flex-col items-start gap-0.5 p-3 rounded-xl cursor-pointer", store.selectedModel === "einstein" && "bg-muted")}>
                  <div className="flex items-center justify-between w-full">
                    <span className="font-bold text-sm">Einstein</span>
                    {store.selectedModel === "einstein" && <Check className="w-4 h-4 text-foreground" />}
                  </div>
                  <span className="text-[11px] text-muted-foreground">Great for complex work</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-hidden relative">
            {store.messages.length === 0 ? (
              /* Empty State */
              <div className="flex-1 flex flex-col items-center justify-center p-6 h-full relative pb-28">
                <div className="w-full max-w-xl flex items-center justify-center gap-3 select-none mb-8">
                  <Persona
                    className="size-10 shrink-0"
                    state="idle"
                    variant="opal"
                  />
                  <h1 className="text-2xl font-medium tracking-tight text-foreground transition-all duration-300 ease-out">
                    {greeting}
                  </h1>
                </div>

                {/* Centered Single Line Input Box */}
                <div className="w-full max-w-xl relative z-20">
                  <ChatInput onSend={handleSend} disabled={false} placeholder={hoveredPrompt || inputPlaceholder} />
                </div>
                
                {/* Quick Work Ideas */}
                <div className="w-full max-w-xl min-h-[250px] relative">
                  {activeIdea ? (
                    <div className="absolute top-4 inset-x-0 bg-card border rounded-2xl shadow-md overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                      <div className="flex items-center justify-between p-4 pb-2 text-muted-foreground">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                          <activeIdea.icon className="w-4 h-4" />
                          {activeIdea.label}
                        </div>
                        <button onClick={() => setActiveIdeaId(null)} className="hover:text-foreground cursor-pointer transition-colors">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="flex flex-col px-2 pb-2">
                        {activeIdea.prompts.map((prompt, i) => (
                          <React.Fragment key={i}>
                            <button
                              className="flex items-center justify-between p-3 text-sm text-left hover:bg-muted/50 rounded-xl transition-colors text-foreground/90 group"
                              onClick={() => {
                                setInputPlaceholder(prompt)
                                setActiveIdeaId(null)
                              }}
                              onMouseEnter={() => setHoveredPrompt(prompt)}
                              onMouseLeave={() => setHoveredPrompt(null)}
                            >
                              {prompt}
                              <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                            </button>
                            {i < activeIdea.prompts.length - 1 && <div className="h-px bg-border/40 mx-3" />}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="absolute top-4 inset-x-0 flex flex-wrap gap-2 items-center justify-center select-none animate-in fade-in slide-in-from-top-2 duration-200">
                      {WORK_IDEAS.map((idea) => (
                        <button 
                          key={idea.id}
                          onClick={() => setActiveIdeaId(idea.id)}
                          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-muted/40 hover:bg-muted text-foreground text-sm font-medium transition-colors border border-border/50 cursor-pointer"
                        >
                          <idea.icon className="w-4 h-4 text-muted-foreground" />
                          {idea.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* Active Conversation Layout */
              <MessageScroller className="flex flex-col h-full bg-background relative w-full flex-grow">
                <MessageScrollerViewport>
                  <MessageScrollerContent className="pb-36 max-w-3xl mx-auto px-4 w-full">
                    
                    {store.messages.map((message, index) => {
                      const nextMessage = store.messages[index + 1]
                      const isNextAlsoAgent = nextMessage && nextMessage.role !== "user"
                      const hideActionsDefault = message.role !== "user" && isNextAlsoAgent

                      const isCurrentStream = message.id === store.streamingMessageId
                      const isActiveStream = isCurrentStream && isStreaming
                      const hasStartedReplying = (message.content?.length || 0) > 0
                      const isActivelyWorking = isActiveStream && !hasStartedReplying
                      const isUser = message.role === "user"

                      let isTaskOpen = openStates[`${message.id}-working`] ?? isCurrentStream
                      if (userRole === "simplified") {
                        isTaskOpen = openStates[`${message.id}-working`] ?? false
                      }

                      const baseTimer = taskTimers[message.id] || { elapsed: message.events?.filter(e => e.type !== "text")?.length || 1, completed: true }

                      return (
                        <ChatMessage
                          key={message.id}
                          message={message}
                          isUser={isUser}
                          userRole={userRole}
                          isTaskOpen={isTaskOpen}
                          onTaskOpenChange={(open: boolean) => setOpenStates((prev) => ({ ...prev, [`${message.id}-working`]: open }))}
                          onOpenSources={() => store.setActiveSourcesMessageId(message.id)}
                          taskTimer={{ elapsed: baseTimer.elapsed, completed: !isActivelyWorking }}
                          personaLoaded={personaLoaded[`${message.id}-persona`] || false}
                          onPersonaLoad={() => setPersonaLoaded((prev) => ({ ...prev, [`${message.id}-persona`]: true }))}
                          onOpenCanvas={(content) => {
                            store.setActiveCanvasContent(content)
                            store.setCanvasOpen(true)
                          }}
                          onResolveInterrupt={handleResolveElicitation}
                          isCompletedResponse={!(isStreaming && isCurrentStream)}
                          hideActionsDefault={hideActionsDefault}
                        />
                      )
                    })}

                    {/* Naked Shimmer Thinking Indicator with animated Persona blob next to it */}
                    {isThinking && (
                      <MessageScrollerItem messageId="shimmer-loading">
                        <div className="flex items-center gap-3 py-1 px-4 my-2 select-none">
                          <Persona
                            className={cn(
                              "transition-all duration-300 shrink-0",
                              !personaLoaded["thinking"] ? "opacity-0 w-0 h-0" : "opacity-100 size-6"
                            )}
                            state="idle"
                            variant="opal"
                            onLoad={() => setPersonaLoaded((prev) => ({ ...prev, thinking: true }))}
                          />
                          <span className="shimmer text-[13px] font-semibold">
                            Thinking...
                          </span>
                        </div>
                      </MessageScrollerItem>
                    )}

                    <div className="h-32 shrink-0 w-full" />
                  </MessageScrollerContent>
                </MessageScrollerViewport>

                {store.messages.length > 0 && <MessageScrollerButton className="bottom-32" />}

                {/* Chat Input Container */}
                <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-background via-background to-transparent flex justify-center pb-6 z-10 select-none">
                  <div className="w-full max-w-[615px] flex flex-col items-center">
                    {activeElicitationMessage && activeElicitationMessage.elicitation && (
                      <ElicitationPanel
                        elicitation={activeElicitationMessage.elicitation}
                        onResolve={(_, value) => handleResolveElicitation(activeElicitationMessage.id, value)}
                        onSkip={() => handleResolveElicitation(activeElicitationMessage.id, "Skipped")}
                        onDismiss={() => handleResolveElicitation(activeElicitationMessage.id, "Dismissed")}
                      />
                    )}
                    <ChatInput 
                      onSend={handleSend} 
                      disabled={hasUnresolvedElicitation} 
                      placeholder={hasUnresolvedElicitation ? "Awaiting decision above..." : "Ask a follow up question..."}
                    />
                  </div>
                </div>
              </MessageScroller>
            )}
          </div>
        </div>

        {/* Canva (Side Panel) */}
        {store.isCanvasOpen && (
          <ChatCanvas 
            activeCanvasContent={store.activeCanvasContent}
            setCanvaOpen={store.setCanvasOpen}
          />
        )}
      </div>

      {store.activeSourcesMessageId && activeSourcesMessage?.sources && (
        <SourcesSidebar
          sources={activeSourcesMessage.sources as any}
          onClose={() => store.setActiveSourcesMessageId(null)}
        />
      )}
    </div>
  )
}

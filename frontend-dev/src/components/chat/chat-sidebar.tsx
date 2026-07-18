import * as React from "react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Sparkles, Play, RotateCcw, Info, ChevronLeft, ChevronRight, MessageSquare, Bug, Settings, Trash2, Plus, X } from "lucide-react"
import { mockScenarios } from "@/app/chat/mock-chat-scenarios"
import { useChatStore } from "@/store/chat-store"
import type { AgentState, ChatEventBlock, Message } from "@/lib/chat-contract"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger, SheetFooter } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { useShallow } from "zustand/react/shallow"

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
  simulateMessage: (msg: Message) => void
}

type Tab = "scenarios" | "debug" | "settings"

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
  resetSimulation,
  simulateMessage
}: ChatSidebarProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<Tab>("scenarios")
  const store = useChatStore(useShallow((state) => ({
    agentState: state.agentState,
    messages: state.messages,
    streamingMessageId: state.streamingMessageId,
    setAgentState: state.setAgentState,
    appendMessage: state.appendMessage,
    setMessages: state.setMessages,
    updateMessage: state.updateMessage,
  })))
  
  const [autoDebug, setAutoDebug] = React.useState(true)

  // Robust Auto-play logic using effect to avoid closure staleness
  const previousActiveScenarioIdRef = React.useRef(activeScenario.id)
  React.useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    if (
      autoDebug && 
      activeScenario.id !== previousActiveScenarioIdRef.current && 
      activeScenario.id !== "none" &&
      playbackIndex === 0 &&
      !isStreaming
    ) {
      previousActiveScenarioIdRef.current = activeScenario.id
      timeoutId = setTimeout(() => playNextTurn(), 50)
    } else {
      previousActiveScenarioIdRef.current = activeScenario.id
    }

    return () => {
      if (timeoutId !== undefined) clearTimeout(timeoutId)
    }
  }, [activeScenario.id, autoDebug, playNextTurn, playbackIndex, isStreaming])

  const handleScenarioSelect = (id: string) => {
    setSelectedScenarioId(id)
    if (autoDebug) {
      setActiveTab("debug")
    }
  }

  // Sheet State
  const [isSheetOpen, setIsSheetOpen] = React.useState(false)
  const [newMessageRole, setNewMessageRole] = React.useState<"user" | "assistant" | "system">("assistant")
  const [newMessageSender, setNewMessageSender] = React.useState("Agent")
  const [newMessageTimestamp, setNewMessageTimestamp] = React.useState(() => new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}))
  const [newMessageContent, setNewMessageContent] = React.useState("")
  
  // Dynamic Mock Events
  const [addMockEvents, setAddMockEvents] = React.useState(false)
  const [mockEventsList, setMockEventsList] = React.useState<any[]>([
    { type: "thought", content: "Checking available tools and data sets...", playbackDelayMs: 400 },
    { type: "tool_call", content: "Extracted 500 rows.", toolName: "read_file", category: "data_read", playbackDelayMs: 600, status: "completed" }
  ])

  // Dynamic Elicitation
  const [addMockElicitation, setAddMockElicitation] = React.useState(false)
  const [mockEliQuestion, setMockEliQuestion] = React.useState("Are you sure you want to proceed?")
  const [mockEliOptions, setMockEliOptions] = React.useState<string[]>(["Yes", "No"])

  // Dynamic Attachments
  const [addMockAttachments, setAddMockAttachments] = React.useState(false)
  const [mockAttachmentsList, setMockAttachmentsList] = React.useState<{name: string, size: string, type: string}[]>([
    { name: "dataset.csv", size: "1.2 MB", type: "CSV" }
  ])
  
  // Canvas payload
  const [addMockCanvas, setAddMockCanvas] = React.useState(false)
  const [canvasTitle, setCanvasTitle] = React.useState("Analysis Chart")
  const [canvasVisualType, setCanvasVisualType] = React.useState<"chart" | "simulation" | "code">("chart")

  const [mockTimesAndSteps, setMockTimesAndSteps] = React.useState(true)

  React.useEffect(() => {
    if (newMessageRole === "user" && (newMessageSender === "Agent" || newMessageSender === "System")) {
      setNewMessageSender("Developer")
    } else if (newMessageRole === "assistant" && (newMessageSender === "Developer" || newMessageSender === "System")) {
      setNewMessageSender("Agent")
    } else if (newMessageRole === "system" && (newMessageSender === "Developer" || newMessageSender === "Agent")) {
      setNewMessageSender("System")
    }
  }, [newMessageRole, newMessageSender])


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
          {/* Top Tab Navigation */}
          <div className="flex items-center gap-1.5 p-3 border-b shrink-0 bg-muted/20">
            <Button 
              variant={activeTab === "scenarios" ? "secondary" : "ghost"} 
              size="icon" 
              onClick={() => setActiveTab("scenarios")} 
              title="Scenarios"
              className={cn("rounded-xl w-9 h-9", activeTab === "scenarios" && "shadow-sm border border-border/50")}
            >
              <MessageSquare className="w-4 h-4" />
            </Button>
            <Button 
              variant={activeTab === "debug" ? "secondary" : "ghost"} 
              size="icon" 
              onClick={() => setActiveTab("debug")} 
              title="State Editor"
              className={cn("rounded-xl w-9 h-9", activeTab === "debug" && "shadow-sm border border-border/50")}
            >
              <Bug className="w-4 h-4" />
            </Button>
            <Button 
              variant={activeTab === "settings" ? "secondary" : "ghost"} 
              size="icon" 
              onClick={() => setActiveTab("settings")} 
              title="Settings"
              className={cn("rounded-xl w-9 h-9", activeTab === "settings" && "shadow-sm border border-border/50")}
            >
              <Settings className="w-4 h-4" />
            </Button>
            
            <div className="flex-1" />
            
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsCollapsed(true)}
              className="h-8 w-8 rounded-lg hover:bg-muted cursor-pointer shrink-0"
              title="Collapse Test System Panel"
            >
              <ChevronLeft className="w-4 h-4 text-muted-foreground" />
            </Button>
          </div>

          {/* Scrollable Tab Content */}
          <ScrollArea className="flex-1 min-h-0">
            {activeTab === "scenarios" && (
              <div className="p-4 space-y-4">
                <div className="space-y-2">
                  <label className="text-[11px] font-bold text-muted-foreground uppercase">
                    Select Scenario
                  </label>
                  <div className="flex flex-col gap-1">
                    {mockScenarios.map((scenario) => (
                      <button
                        key={scenario.id}
                        onClick={() => handleScenarioSelect(scenario.id)}
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
                  
                  <div className="flex items-center space-x-2 mt-4 pt-2">
                    <Checkbox id="auto-debug" checked={autoDebug} onCheckedChange={(c) => setAutoDebug(!!c)} />
                    <Label htmlFor="auto-debug" className="text-[11px] font-medium leading-none cursor-pointer">
                      Auto-switch & Play in Debug tab
                    </Label>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "debug" && (
              <div className="p-4 space-y-6 pb-20">
                <div className="space-y-3">
                  <label className="text-[11px] font-bold text-muted-foreground uppercase">
                    Global State
                  </label>
                  <div className="space-y-2">
                    <div className="flex flex-col gap-1.5">
                      <Label className="text-[10px] text-muted-foreground font-normal">Agent State</Label>
                      <Select 
                        value={store.agentState}
                        onValueChange={(val) => store.setAgentState(val as AgentState)}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Select agent state" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="idle">idle</SelectItem>
                          <SelectItem value="thinking">thinking</SelectItem>
                          <SelectItem value="working">working</SelectItem>
                          <SelectItem value="waiting_for_user">waiting_for_user</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 border-t pt-4">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-bold text-muted-foreground uppercase">
                      Messages ({store.messages.length})
                    </label>
                    <div className="flex items-center gap-1">
                      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
                        <SheetTrigger asChild>
                          <Button variant="outline" size="sm" className="h-6 text-[10px] px-2">
                            Create
                          </Button>
                        </SheetTrigger>
                        <SheetContent side="right" className="w-[400px] sm:w-[540px] p-0 flex flex-col h-full overflow-hidden">
                          <SheetHeader className="p-4 border-b flex-none space-y-0 text-left">
                            <SheetTitle className="text-lg font-bold pr-6">Create Custom Message</SheetTitle>
                          </SheetHeader>
                          
                          <div className="flex-1 overflow-y-auto p-6 space-y-5 pb-12">
                            <div className="grid grid-cols-2 gap-4">
                              <div className="space-y-2">
                                <Label>Role</Label>
                                <Select value={newMessageRole} onValueChange={(val: any) => setNewMessageRole(val)}>
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="user">User</SelectItem>
                                    <SelectItem value="assistant">Assistant</SelectItem>
                                    <SelectItem value="system">System</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-2">
                                <Label>Timestamp</Label>
                                <Input 
                                  value={newMessageTimestamp} 
                                  onChange={(e) => setNewMessageTimestamp(e.target.value)} 
                                  placeholder="e.g. 10:42 AM" 
                                />
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              <Label>Sender Name</Label>
                              <Input 
                                value={newMessageSender} 
                                onChange={(e) => setNewMessageSender(e.target.value)} 
                                placeholder="e.g. Agent, User, System..." 
                              />
                            </div>
                            
                            <div className="space-y-2">
                              <Label>Content (Text)</Label>
                              <Textarea 
                                value={newMessageContent} 
                                onChange={(e) => setNewMessageContent(e.target.value)} 
                                placeholder="Type message content..."
                                className="min-h-[100px] resize-y"
                              />
                            </div>

                            <div className="space-y-4 pt-4 border-t">
                              <Label className="text-base font-semibold">Mock Add-ons</Label>
                              
                              <div className="flex items-center space-x-2 pb-2">
                                <Switch id="mock-times" checked={mockTimesAndSteps} onCheckedChange={setMockTimesAndSteps} />
                                <Label htmlFor="mock-times" className="text-sm font-medium cursor-pointer">Simulate animation delays & streams</Label>
                              </div>

                              {/* Events Builder */}
                              <div className={cn("flex flex-col gap-3 border rounded-lg p-3 transition-colors", addMockEvents ? "bg-muted/30" : "")}>
                                <div className="flex items-center justify-between">
                                  <div className="space-y-0.5">
                                    <Label htmlFor="mock-events" className="text-sm font-medium">Add Mock Events</Label>
                                    <p className="text-xs text-muted-foreground">Injects a mock thought and tool block.</p>
                                  </div>
                                  <Switch id="mock-events" checked={addMockEvents} onCheckedChange={setAddMockEvents} />
                                </div>
                                {addMockEvents && (
                                  <div className="flex flex-col gap-3 pt-2 mt-2 border-t">
                                    {mockEventsList.map((ev, i) => (
                                      <div key={i} className="flex flex-col gap-2 bg-background p-2 rounded-lg border">
                                        <div className="flex items-start gap-2">
                                          <div className="flex-1 space-y-2">
                                            <div className="flex gap-2">
                                              <Select value={ev.type} onValueChange={(val: any) => {
                                                const newEvents = [...mockEventsList]
                                                newEvents[i].type = val
                                                setMockEventsList(newEvents)
                                              }}>
                                                <SelectTrigger className="h-7 text-xs w-[110px] shrink-0">
                                                  <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                  <SelectItem value="thought">Thought</SelectItem>
                                                  <SelectItem value="tool_call">Tool Call</SelectItem>
                                                  <SelectItem value="artifact_update">Artifact</SelectItem>
                                                  <SelectItem value="interrupt">Interrupt</SelectItem>
                                                  <SelectItem value="status_pulse">Status Pulse</SelectItem>
                                                </SelectContent>
                                              </Select>
                                              
                                              {ev.type === "tool_call" && (
                                                <>
                                                  <Input 
                                                    value={ev.toolName || ""} 
                                                    onChange={(e) => {
                                                      const newEvents = [...mockEventsList]
                                                      newEvents[i].toolName = e.target.value
                                                      setMockEventsList(newEvents)
                                                    }} 
                                                    className="h-7 text-xs flex-1" 
                                                    placeholder="Tool (e.g. read_file)"
                                                  />
                                                  <Select value={ev.category || "data_read"} onValueChange={(val: any) => {
                                                    const newEvents = [...mockEventsList]
                                                    newEvents[i].category = val
                                                    setMockEventsList(newEvents)
                                                  }}>
                                                    <SelectTrigger className="h-7 text-xs w-[120px] shrink-0">
                                                      <SelectValue placeholder="Category" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                      <SelectItem value="data_read">data_read</SelectItem>
                                                      <SelectItem value="web_search">web_search</SelectItem>
                                                      <SelectItem value="validation">validation</SelectItem>
                                                      <SelectItem value="calendar">calendar</SelectItem>
                                                      <SelectItem value="file_inspect">file_inspect</SelectItem>
                                                      <SelectItem value="code_execution">code_execution</SelectItem>
                                                      <SelectItem value="grading">grading</SelectItem>
                                                      <SelectItem value="delegation">delegation</SelectItem>
                                                      <SelectItem value="communication">communication</SelectItem>
                                                    </SelectContent>
                                                  </Select>
                                                </>
                                              )}
                                            </div>

                                            <div className="flex gap-2 items-center">
                                              <Input 
                                                value={ev.content || ""} 
                                                onChange={(e) => {
                                                  const newEvents = [...mockEventsList]
                                                  newEvents[i].content = e.target.value
                                                  setMockEventsList(newEvents)
                                                }} 
                                                className="h-7 text-xs flex-1" 
                                                placeholder={ev.type === "tool_call" ? "Result summary or label..." : "Event content..."}
                                              />
                                              
                                              <span className="text-[10px] text-muted-foreground whitespace-nowrap">Delay (ms)</span>
                                              <Input
                                                type="number"
                                                value={ev.playbackDelayMs || 0}
                                                onChange={(e) => {
                                                  const newEvents = [...mockEventsList]
                                                  newEvents[i].playbackDelayMs = parseInt(e.target.value) || 0
                                                  setMockEventsList(newEvents)
                                                }}
                                                className="h-7 text-xs w-[70px] shrink-0"
                                              />
                                            </div>
                                          </div>
                                          <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:bg-destructive/10 shrink-0" onClick={() => setMockEventsList(mockEventsList.filter((_, idx) => idx !== i))}>
                                            <X className="w-3 h-3" />
                                          </Button>
                                        </div>
                                      </div>
                                    ))}
                                    <Button variant="outline" size="sm" className="h-7 text-xs border-dashed" onClick={() => setMockEventsList([...mockEventsList, {type: "thought", content: "New event..."}])}>
                                      <Plus className="w-3 h-3 mr-1" /> Add Event
                                    </Button>
                                  </div>
                                )}
                              </div>
                              
                              {/* Elicitation Builder */}
                              <div className={cn("flex flex-col gap-3 border rounded-lg p-3 transition-colors", addMockElicitation ? "bg-muted/30" : "")}>
                                <div className="flex items-center justify-between">
                                  <div className="space-y-0.5">
                                    <Label htmlFor="mock-eli" className="text-sm font-medium">Attach Elicitation</Label>
                                    <p className="text-xs text-muted-foreground">Appends a mock multiple-choice question.</p>
                                  </div>
                                  <Switch id="mock-eli" checked={addMockElicitation} onCheckedChange={setAddMockElicitation} />
                                </div>
                                {addMockElicitation && (
                                  <div className="flex flex-col gap-3 pt-2 mt-2 border-t">
                                    <div className="space-y-1.5">
                                      <Label className="text-xs text-muted-foreground">Question Title</Label>
                                      <Input value={mockEliQuestion} onChange={(e) => setMockEliQuestion(e.target.value)} className="h-8 text-xs bg-background" />
                                    </div>
                                    <div className="space-y-2">
                                      <Label className="text-xs text-muted-foreground">Options</Label>
                                      <div className="flex flex-col gap-2">
                                        {mockEliOptions.map((opt, i) => (
                                          <div key={i} className="flex items-center gap-2">
                                            <div className="bg-muted text-muted-foreground w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold shrink-0 border">
                                              {i + 1}
                                            </div>
                                            <Input 
                                              value={opt} 
                                              onChange={(e) => {
                                                const newOpts = [...mockEliOptions]
                                                newOpts[i] = e.target.value
                                                setMockEliOptions(newOpts)
                                              }} 
                                              className="h-8 text-xs bg-background flex-1" 
                                              placeholder={`Option ${i+1}`}
                                            />
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10 shrink-0" onClick={() => setMockEliOptions(mockEliOptions.filter((_, idx) => idx !== i))}>
                                              <X className="w-3 h-3" />
                                            </Button>
                                          </div>
                                        ))}
                                      </div>
                                      <Button variant="outline" size="sm" className="w-full h-7 text-xs border-dashed mt-1" onClick={() => setMockEliOptions([...mockEliOptions, "New Option"])}>
                                        <Plus className="w-3 h-3 mr-1" /> Add Option
                                      </Button>
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Attachment Builder */}
                              <div className={cn("flex flex-col gap-3 border rounded-lg p-3 transition-colors", addMockAttachments ? "bg-muted/30" : "")}>
                                <div className="flex items-center justify-between">
                                  <div className="space-y-0.5">
                                    <Label htmlFor="mock-attach" className="text-sm font-medium">Add Mock Attachment</Label>
                                    <p className="text-xs text-muted-foreground">Simulates uploaded files on the message.</p>
                                  </div>
                                  <Switch id="mock-attach" checked={addMockAttachments} onCheckedChange={setAddMockAttachments} />
                                </div>
                                {addMockAttachments && (
                                  <div className="flex flex-col gap-3 pt-2 mt-2 border-t">
                                    {mockAttachmentsList.map((att, i) => (
                                      <div key={i} className="grid grid-cols-6 gap-2 items-end bg-background p-2 rounded-lg border relative">
                                        <Button variant="ghost" size="icon" className="absolute -top-2 -right-2 h-5 w-5 bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-full shadow" onClick={() => setMockAttachmentsList(mockAttachmentsList.filter((_, idx) => idx !== i))}>
                                          <X className="w-3 h-3" />
                                        </Button>
                                        <div className="space-y-1.5 col-span-3">
                                          <Label className="text-[10px] text-muted-foreground">File Name</Label>
                                          <Input value={att.name} onChange={(e) => {
                                            const newList = [...mockAttachmentsList]
                                            newList[i].name = e.target.value
                                            setMockAttachmentsList(newList)
                                          }} className="h-7 text-xs" />
                                        </div>
                                        <div className="space-y-1.5 col-span-2">
                                          <Label className="text-[10px] text-muted-foreground">Size</Label>
                                          <Input value={att.size} onChange={(e) => {
                                            const newList = [...mockAttachmentsList]
                                            newList[i].size = e.target.value
                                            setMockAttachmentsList(newList)
                                          }} className="h-7 text-xs" />
                                        </div>
                                        <div className="space-y-1.5 col-span-1">
                                          <Label className="text-[10px] text-muted-foreground">Type</Label>
                                          <Input value={att.type} onChange={(e) => {
                                            const newList = [...mockAttachmentsList]
                                            newList[i].type = e.target.value
                                            setMockAttachmentsList(newList)
                                          }} className="h-7 text-xs px-1 text-center" />
                                        </div>
                                      </div>
                                    ))}
                                    <Button variant="outline" size="sm" className="h-7 text-xs border-dashed" onClick={() => setMockAttachmentsList([...mockAttachmentsList, {name: "file.pdf", size: "1 MB", type: "PDF"}])}>
                                      <Plus className="w-3 h-3 mr-1" /> Add Attachment
                                    </Button>
                                  </div>
                                )}
                              </div>

                              {/* Canvas Builder */}
                              <div className={cn("flex flex-col gap-3 border rounded-lg p-3 transition-colors", addMockCanvas ? "bg-muted/30" : "")}>
                                <div className="flex items-center justify-between">
                                  <div className="space-y-0.5">
                                    <Label htmlFor="mock-canvas" className="text-sm font-medium">Inject Canvas Payload</Label>
                                    <p className="text-xs text-muted-foreground">Appends a Canvas view to this message.</p>
                                  </div>
                                  <Switch id="mock-canvas" checked={addMockCanvas} onCheckedChange={setAddMockCanvas} />
                                </div>
                                {addMockCanvas && (
                                  <div className="grid grid-cols-2 gap-3 pt-2 mt-2 border-t">
                                    <div className="space-y-1.5">
                                      <Label className="text-xs text-muted-foreground">Title</Label>
                                      <Input 
                                        value={canvasTitle} 
                                        onChange={(e) => setCanvasTitle(e.target.value)} 
                                        className="h-8 text-xs bg-background" 
                                      />
                                    </div>
                                    <div className="space-y-1.5">
                                      <Label className="text-xs text-muted-foreground">Visual Type</Label>
                                      <Select value={canvasVisualType} onValueChange={(val: any) => setCanvasVisualType(val)}>
                                        <SelectTrigger className="h-8 text-xs bg-background">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="chart">Chart</SelectItem>
                                          <SelectItem value="simulation">Simulation</SelectItem>
                                          <SelectItem value="code">Code / Document</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          <SheetFooter className="p-4 border-t flex-none bg-background/80 backdrop-blur-md">
                            <div className="flex items-center justify-end w-full gap-2">
                              <Button variant="outline" onClick={() => setIsSheetOpen(false)}>Cancel</Button>
                              <Button onClick={() => {
                                const newMsg: Message = {
                                  id: "msg_custom_" + Date.now(),
                                  role: newMessageRole,
                                  senderName: newMessageSender,
                                  timestamp: newMessageTimestamp,
                                  content: newMessageContent,
                                }
                                if (addMockEvents) {
                                  newMsg.events = mockEventsList.map(ev => {
                                    if (ev.type === "thought") {
                                      return { type: "thought", content: ev.content, playbackDelayMs: ev.playbackDelayMs }
                                    } else if (ev.type === "tool_call") {
                                      return { type: "tool_call", toolName: ev.toolName || "tool", category: ev.category || "data_read", status: ev.status || "completed", resultSummary: ev.content, label: ev.content, playbackDelayMs: ev.playbackDelayMs }
                                    } else if (ev.type === "artifact_update") {
                                      return { type: "artifact_update", action: "create", artifactName: ev.content, content: ev.content, playbackDelayMs: ev.playbackDelayMs }
                                    } else if (ev.type === "interrupt") {
                                      return { type: "interrupt", content: ev.content, status: "awaiting_input", playbackDelayMs: ev.playbackDelayMs }
                                    } else if (ev.type === "status_pulse") {
                                      return { type: "status_pulse", content: ev.content, playbackDelayMs: ev.playbackDelayMs }
                                    }
                                    return { type: "text", content: ev.content }
                                  }) as ChatEventBlock[]
                                }
                                if (addMockElicitation) {
                                  newMsg.elicitation = {
                                    id: "eli_inline_" + Date.now(),
                                    questions: [{ 
                                      id: "q_in_1", 
                                      title: mockEliQuestion, 
                                      options: mockEliOptions.map((opt, i) => ({ label: opt, value: `opt${i}` }))
                                    }]
                                  }
                                }
                                if (addMockAttachments) {
                                  newMsg.attachments = mockAttachmentsList.map(att => ({ ...att, isImage: false }))
                                }
                                if (addMockCanvas) {
                                  newMsg.canvasContent = {
                                    title: canvasTitle,
                                    type: canvasVisualType === "code" ? "Code Block" : "Interactive View",
                                    visualType: canvasVisualType,
                                    code: canvasVisualType === "code" ? `// Sample mock code payload\nfunction hello() {\n  return "world";\n}` : undefined
                                  }
                                }

                                if (mockTimesAndSteps) {
                                  simulateMessage(newMsg)
                                } else {
                                  store.appendMessage(newMsg)
                                }
                                setIsSheetOpen(false)
                                setNewMessageContent("")
                              }}>
                                Inject Message
                              </Button>
                            </div>
                          </SheetFooter>
                        </SheetContent>
                      </Sheet>
                      
                      <Button variant="ghost" size="sm" className="h-6 text-[10px] px-2 text-destructive" onClick={() => store.setMessages([])}>
                        Clear
                      </Button>
                    </div>
                  </div>
                  
                  <div className="flex flex-col gap-3">
                    {store.messages.map(msg => (
                      <div key={msg.id} className="bg-muted/30 border rounded-xl p-2.5 space-y-2 relative group">
                        <div className="flex justify-between items-start">
                          <div className="flex items-center gap-1.5">
                            <span className={cn(
                              "text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-md",
                              msg.role === "user" ? "bg-blue-500/10 text-blue-500" : 
                              msg.role === "system" ? "bg-purple-500/10 text-purple-500" : "bg-primary/10 text-primary"
                            )}>
                              {msg.role}
                            </span>
                            <span className="text-[10px] text-muted-foreground truncate max-w-[100px]">{msg.id}</span>
                          </div>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:bg-destructive/10 -mr-1 -mt-1"
                            onClick={() => store.setMessages(store.messages.filter(m => m.id !== msg.id))}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                        
                        <Textarea 
                          className="w-full min-h-[60px] text-xs p-2 rounded-lg resize-y bg-background"
                          value={msg.content}
                          onChange={(e) => store.updateMessage(msg.id, { content: e.target.value })}
                          placeholder="Empty message content..."
                        />
                        
                        <div className="text-[10px] text-muted-foreground flex justify-between">
                          <span>{msg.events?.length || 0} events</span>
                          {store.streamingMessageId === msg.id && (
                            <span className="text-amber-500 font-semibold animate-pulse">Streaming</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "settings" && (
              <div className="p-4 space-y-6">
                <div className="space-y-2 shrink-0">
                  <label className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block">
                    UI Role View
                  </label>
                  <p className="text-[10px] text-muted-foreground mb-2 leading-relaxed">
                    Test the UI dynamically adapting to different extension role permissions.
                  </p>
                  <div className="grid grid-cols-2 gap-1 bg-muted/60 p-0.5 rounded-xl border border-border/50 select-none">
                    {(["simplified", "complete"] as const).map((role) => (
                      <button
                        key={role}
                        onClick={() => setUserRole(role)}
                        className={cn(
                          "py-1.5 text-[10px] font-bold rounded-lg capitalize transition-all cursor-pointer",
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
            )}
          </ScrollArea>

          {/* Bottom Fixed Panels based on Tab */}
          {activeTab === "debug" && (
            <div className="p-4 border-t space-y-3 shrink-0 bg-background/50">
              <label className="text-[11px] font-bold text-muted-foreground uppercase block">
                Simulation Control
              </label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={playNextTurn}
                  disabled={isStreaming || playbackIndex >= activeScenario.messages.length || hasUnresolvedElicitation}
                  className="flex items-center gap-1 text-xs shadow-sm"
                >
                  <Play className="w-3.5 h-3.5" /> Step Next
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => resetSimulation()}
                  className="flex items-center gap-1 text-xs text-destructive hover:bg-destructive/5 shadow-sm"
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
                      width: `${activeScenario.messages.length > 0 ? (playbackIndex / activeScenario.messages.length) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === "settings" && (
            <div className="p-4 border-t bg-muted/20 shrink-0">
              <div className="flex items-start gap-2.5">
                <Info className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                <div className="text-[10px] text-muted-foreground leading-normal font-medium">
                  Auto-scroll keeps output pinned to the bottom. Scroll up manually to pause auto-scrolling.
                </div>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  )
}

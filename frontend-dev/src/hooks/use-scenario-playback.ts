import * as React from "react"
import { mockScenarios, Scenario } from "@/app/chat/mock-chat-scenarios"
import { useChatStore, Message, ChatEventBlock } from "@/store/chat-store"

export function useScenarioPlayback() {
  const store = useChatStore()
  
  // Role view state: simplified or complete
  const [userRole, setUserRole] = React.useState<"simplified" | "complete">("complete")

  // Scenario selector state
  const [selectedScenarioId, setSelectedScenarioId] = React.useState<string>("data-viz-complex")
  const [activeScenario, setActiveScenario] = React.useState<Scenario>(
    mockScenarios.find((s) => s.id === "data-viz-complex") || mockScenarios[0]
  )

  const [isStreaming, setIsStreaming] = React.useState(false)
  const [playbackIndex, setPlaybackIndex] = React.useState(0)
  
  // Collapsible Open/Close tracking state for Working wrapper and Sources
  const [openStates, setOpenStates] = React.useState<Record<string, boolean>>({})

  // State to track loaded Rive persona contexts to prevent blank flashes
  const [personaLoaded, setPersonaLoaded] = React.useState<Record<string, boolean>>({})

  // Handle changing scenarios
  React.useEffect(() => {
    const scenario = mockScenarios.find((s) => s.id === selectedScenarioId) || mockScenarios[0]
    setActiveScenario(scenario)
    resetSimulation(scenario)
  }, [selectedScenarioId])

  // Reset the chat
  const resetSimulation = (scenario = activeScenario) => {
    setIsStreaming(false)
    store.clearChat()
    setPlaybackIndex(0)
    store.setActiveCanvasContent(null)
    store.setCanvasOpen(false)
    setOpenStates({})
    setPersonaLoaded({})
  }

  // Play next turn in the scenario with realistic tool-calling sequence
  const playNextTurn = async () => {
    if (playbackIndex >= activeScenario.messages.length) return
    setIsStreaming(true)

    const nextMsg = activeScenario.messages[playbackIndex]

    // If user message, add it instantly
    if (nextMsg.role === "user") {
      store.appendMessage({ ...nextMsg, events: [] })
      setPlaybackIndex((prev) => prev + 1)
      setIsStreaming(false)
      
      if (nextMsg.canvasContent) {
        store.setActiveCanvasContent(nextMsg.canvasContent)
        store.setCanvasOpen(true)
      }
      return
    }

    // Assistant message: Step-by-step playback simulation
    store.setStreamingMessageId(nextMsg.id)
    store.setAgentState("working")

    // 1. Initial State: add empty message
    store.appendMessage({
      id: nextMsg.id,
      role: "assistant",
      senderName: nextMsg.senderName,
      timestamp: nextMsg.timestamp,
      content: "",
      events: [],
    })

    // Auto-expand the working wrapper initially
    setOpenStates((prev) => ({ ...prev, [`${nextMsg.id}-working`]: true }))

    // Simulated TTT delay
    await new Promise((resolve) => setTimeout(resolve, 600))

    // 2. Stream Events (Thoughts, Tool Calls, Artifacts)
    const fullEvents = nextMsg.events || []
    
    for (let i = 0; i < fullEvents.length; i++) {
      const ev = fullEvents[i]
      
      if (ev.type === "text") {
        // Break out of the event loop to stream the text below
        break;
      } else if (ev.type === "tool_call") {
        // Push running state
        store.addMessageEvent(nextMsg.id, { ...ev, status: "running" })
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 800))
        // Update to completed/failed/error
        store.updateLastMessageEvent(nextMsg.id, () => ev)
      } else if (ev.type === "thought") {
        store.addMessageEvent(nextMsg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || ev.durationMs || 500))
      } else if (ev.type === "artifact_update") {
        store.addMessageEvent(nextMsg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 600))
      } else if (ev.type === "interrupt") {
        store.addMessageEvent(nextMsg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 500))
      } else if (ev.type === "status_pulse") {
        store.addMessageEvent(nextMsg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 500))
      }
    }

    // Collapse working panel when text starts
    setOpenStates((prev) => ({ ...prev, [`${nextMsg.id}-working`]: false }))
    // Continue in "working" state while streaming text

    // 3. Stream Text
    const words = nextMsg.content.split(" ")
    let textBuffer = ""

    for (let i = 0; i < words.length; i++) {
      textBuffer += (i === 0 ? "" : " ") + words[i]
      store.updateMessage(nextMsg.id, { content: textBuffer })
      await new Promise((resolve) => setTimeout(resolve, 40)) // 40ms per word
    }

    // 4. Stream extra payload
    if (nextMsg.sources && nextMsg.sources.length > 0) {
      store.updateMessage(nextMsg.id, { sources: nextMsg.sources })
    }

    if (nextMsg.elicitation) {
      store.updateMessage(nextMsg.id, { elicitation: nextMsg.elicitation })
      store.setActiveElicitation(nextMsg.elicitation)
      store.setAgentState("waiting_for_user")
    } else {
      store.setAgentState("idle")
    }

    if (nextMsg.statusPulse) {
      store.updateMessage(nextMsg.id, { statusPulse: nextMsg.statusPulse })
    }

    if (nextMsg.canvasContent) {
      store.updateMessage(nextMsg.id, { canvasContent: nextMsg.canvasContent })
      await new Promise((resolve) => setTimeout(resolve, 400))
      store.setActiveCanvasContent(nextMsg.canvasContent)
      store.setCanvasOpen(true)
    }

    // 7. Streaming completes
    setIsStreaming(false)
    store.setStreamingMessageId(null)
    setPlaybackIndex((prev) => prev + 1)
  }

  // Auto play the scenario (only if not interrupted by a pending elicitation)
  React.useEffect(() => {
    let timeout: any
    const hasUnresolvedElicitation = store.activeElicitation != null

    if (
      isStreaming === false &&
      playbackIndex < activeScenario.messages.length &&
      playbackIndex > 0 &&
      !hasUnresolvedElicitation
    ) {
      timeout = setTimeout(() => {
        playNextTurn()
      }, 1000)
    }
    return () => clearTimeout(timeout)
  }, [playbackIndex, isStreaming, store.messages, activeScenario])

  // Resolve an elicitation
  const handleResolveElicitation = async (messageId: string, optionLabel: string) => {
    store.setActiveElicitation(null)
    store.updateMessage(messageId, { 
      elicitation: { ...store.messages.find(m => m.id === messageId)!.elicitation!, resolved: true, selectedOption: optionLabel }
    })

    const userMsgId = `user-decision-${Date.now()}`
    const userMsg: Message = {
      id: userMsgId,
      role: "user",
      senderName: userRole === "complete" ? "Professor Allan" : "Student Allan",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: `${optionLabel}`
    }
    store.appendMessage(userMsg)

    // Simulate response only for the orchestration scenario
    if (activeScenario.id === "batch-grade-orchestration") {
      setIsStreaming(true)
      store.setAgentState("working")
      const followUpMsgId = `assistant-followup-${Date.now()}`
      
      store.appendMessage({
        id: followUpMsgId,
        role: "assistant",
        senderName: "Grading Coordinator",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: "",
        events: []
      })

      await new Promise((resolve) => setTimeout(resolve, 600))
      setOpenStates((prev) => ({ ...prev, [`${followUpMsgId}-working`]: true }))
      
      store.addMessageEvent(followUpMsgId, { type: "thought", content: "User accepted provisional grades. Generating final PDF report...", durationMs: 800 })
      await new Promise((resolve) => setTimeout(resolve, 800))
      
      store.addMessageEvent(followUpMsgId, { type: "tool_call", toolName: "write_file", args: { path: "semester_report.pdf" }, status: "completed", resultSummary: "Generated PDF." })
      await new Promise((resolve) => setTimeout(resolve, 600))
      
      setOpenStates((prev) => ({ ...prev, [`${followUpMsgId}-working`]: false }))

      const content = "Understood — applying provisional grades. I have generated the audited semester report PDF for you."
      const words = content.split(" ")
      let textBuffer = ""
      for (let i = 0; i < words.length; i++) {
        textBuffer += (i === 0 ? "" : " ") + words[i]
        store.updateMessage(followUpMsgId, { content: textBuffer })
        await new Promise((resolve) => setTimeout(resolve, 40))
      }

      store.updateMessage(followUpMsgId, { 
        canvasContent: {
          title: "Semester Performance Report Summary",
          type: "PDF · Document",
          visualType: "code",
          code: `FAIR Grading Audit Report - HW3\nStatus: Audited\nDecided Action: Provisional Grades Accepted\nMedian Class Score: 74/100`
        }
      })
      
      store.setActiveCanvasContent(store.messages.find(m => m.id === followUpMsgId)!.canvasContent!)
      store.setCanvasOpen(true)
      
      setIsStreaming(false)
      store.setStreamingMessageId(null)
      store.setAgentState("idle")
    }
  }

  const handleSend = (inputValue: string, uploadedFiles: any[]) => {
    if (!inputValue.trim() && uploadedFiles.length === 0) return

    const newMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      senderName: "Allan",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: inputValue,
      attachments: uploadedFiles.map(f => ({ ...f, isImage: false })),
    }

    store.appendMessage(newMsg)
  }

  // Simulate a custom message (mocks times and steps)
  const simulateMessage = async (msg: Message) => {
    if (isStreaming) return
    setIsStreaming(true)
    store.setAgentState("working")
    store.setStreamingMessageId(msg.id)
    setOpenStates((prev) => ({ ...prev, [`${msg.id}-working`]: true }))

    // Add empty shell message
    store.appendMessage({ ...msg, content: "", events: [], sources: [], canvasContent: undefined, statusPulse: undefined, elicitation: undefined })
    await new Promise((resolve) => setTimeout(resolve, 600))

    const fullEvents = msg.events || []
    for (let i = 0; i < fullEvents.length; i++) {
      const ev = fullEvents[i]
      if (ev.type === "text") break
      else if (ev.type === "tool_call") {
        store.addMessageEvent(msg.id, { ...ev, status: "running" })
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 800))
        store.updateLastMessageEvent(msg.id, () => ev)
      } else if (ev.type === "thought") {
        store.addMessageEvent(msg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || ev.durationMs || 500))
      } else if (ev.type === "artifact_update") {
        store.addMessageEvent(msg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 600))
      } else if (ev.type === "interrupt") {
        store.addMessageEvent(msg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 500))
      } else if (ev.type === "status_pulse") {
        store.addMessageEvent(msg.id, ev)
        await new Promise((resolve) => setTimeout(resolve, ev.playbackDelayMs || 500))
      }
    }

    setOpenStates((prev) => ({ ...prev, [`${msg.id}-working`]: false }))

    const words = msg.content.split(" ")
    let textBuffer = ""
    for (let i = 0; i < words.length; i++) {
      textBuffer += (i === 0 ? "" : " ") + words[i]
      store.updateMessage(msg.id, { content: textBuffer })
      await new Promise((resolve) => setTimeout(resolve, 40))
    }

    if (msg.sources && msg.sources.length > 0) store.updateMessage(msg.id, { sources: msg.sources })
    if (msg.statusPulse) store.updateMessage(msg.id, { statusPulse: msg.statusPulse })

    if (msg.canvasContent) {
      store.updateMessage(msg.id, { canvasContent: msg.canvasContent })
      await new Promise((resolve) => setTimeout(resolve, 400))
      store.setActiveCanvasContent(msg.canvasContent)
      store.setCanvasOpen(true)
    }

    if (msg.elicitation) {
      store.updateMessage(msg.id, { elicitation: msg.elicitation })
      store.setActiveElicitation(msg.elicitation)
      store.setAgentState("waiting_for_user")
    } else {
      store.setAgentState("idle")
    }

    setIsStreaming(false)
    store.setStreamingMessageId(null)
  }

  return {
    userRole,
    setUserRole,
    selectedScenarioId,
    setSelectedScenarioId,
    activeScenario,
    messages: store.messages,
    isStreaming,
    playbackIndex,
    openStates,
    setOpenStates,
    personaLoaded,
    setPersonaLoaded,
    streamingMessageId: store.streamingMessageId,
    resetSimulation,
    playNextTurn,
    handleResolveElicitation,
    handleSend,
    simulateMessage
  }
}

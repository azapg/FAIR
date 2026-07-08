import * as React from "react"
import { mockScenarios, Scenario, MockMessage } from "@/app/chat/mock-chat-scenarios"

export function useScenarioPlayback() {
  // Role view state: simplified or complete
  const [userRole, setUserRole] = React.useState<"simplified" | "complete">("complete")

  // Scenario selector state
  const [selectedScenarioId, setSelectedScenarioId] = React.useState<string>("tb-cases")
  const [activeScenario, setActiveScenario] = React.useState<Scenario>(
    mockScenarios.find((s) => s.id === "tb-cases") || mockScenarios[0]
  )

  // Simulation states
  const [messages, setMessages] = React.useState<MockMessage[]>([])
  const [currentStreamingText, setCurrentStreamingText] = React.useState<string>("")
  const [streamingMessageId, setStreamingMessageId] = React.useState<string | null>(null)
  const [isStreaming, setIsStreaming] = React.useState(false)
  const [playbackIndex, setPlaybackIndex] = React.useState(0)
  
  // Canva state
  const [canvaOpen, setCanvaOpen] = React.useState(true)
  const [activeCanvasContent, setActiveCanvasContent] = React.useState<any>(null)

  // Collapsible Open/Close tracking state for Tasks and Sources
  const [openStates, setOpenStates] = React.useState<Record<string, boolean>>({})

  // Timer states for the Working/Worked checklist title
  const [taskTimers, setTaskTimers] = React.useState<Record<string, { elapsed: number; completed: boolean }>>({})

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
    setMessages([])
    setCurrentStreamingText("")
    setStreamingMessageId(null)
    setPlaybackIndex(0)
    setActiveCanvasContent(null)
    setOpenStates({})
    setTaskTimers({})
    setPersonaLoaded({})
  }

  // Play next turn in the scenario with realistic tool-calling sequence
  const playNextTurn = async () => {
    if (playbackIndex >= activeScenario.messages.length) return
    setIsStreaming(true)

    const nextMsg = activeScenario.messages[playbackIndex]

    // If user message, add it instantly
    if (nextMsg.role === "user") {
      setMessages((prev) => [...prev, nextMsg])
      setPlaybackIndex((prev) => prev + 1)
      setIsStreaming(false)
      
      // Auto-open canvas if user message triggers canvas content
      if (nextMsg.canvasContent) {
        setActiveCanvasContent(nextMsg.canvasContent)
      }
      return
    }

    // Assistant message: Step-by-step playback simulation
    setStreamingMessageId(nextMsg.id)

    // 1. Initial State: add empty message, show Thinking...
    setMessages((prev) => [
      ...prev,
      {
        id: nextMsg.id,
        role: "assistant",
        senderName: nextMsg.senderName,
        timestamp: nextMsg.timestamp,
        content: "",
        tasks: [],
      },
    ])

    // Simulated TTT delay: 200ms - 1200ms before working panel appears
    const tttDelay = 200 + Math.floor(Math.random() * 1000)
    await new Promise((resolve) => setTimeout(resolve, tttDelay))

    // Initialize task timer tracking
    const startTime = Date.now()
    setTaskTimers((prev) => ({
      ...prev,
      [nextMsg.id]: { elapsed: 0, completed: false }
    }))

    const timerInterval = setInterval(() => {
      setTaskTimers((prev) => {
        const current = prev[nextMsg.id]
        if (!current || current.completed) {
          clearInterval(timerInterval)
          return prev
        }
        return {
          ...prev,
          [nextMsg.id]: { ...current, elapsed: Math.floor((Date.now() - startTime) / 1000) }
        }
      })
    }, 100)

    // 2. Stream Tasks (Tools usage simulation)
    const fullTasks = nextMsg.tasks || []
    const currentTasks: any[] = []

    for (let i = 0; i < fullTasks.length; i++) {
      // Spawn current task in "running" state
      const runningTask = { ...fullTasks[i], state: "running" as const }
      currentTasks.push(runningTask)
      
      setMessages((prev) =>
        prev.map((m) => (m.id === nextMsg.id ? { ...m, tasks: [...currentTasks] } : m))
      )
      setOpenStates((prev) => ({ ...prev, [`${nextMsg.id}-tasks`]: true }))

      // Wait 1200ms to simulate tool execution
      await new Promise((resolve) => setTimeout(resolve, 1200))

      // Complete the task
      currentTasks[i] = { ...fullTasks[i], state: fullTasks[i].state }
      setMessages((prev) =>
        prev.map((m) => (m.id === nextMsg.id ? { ...m, tasks: [...currentTasks] } : m))
      )
    }

    // Mark task timer as completed
    setTaskTimers((prev) => {
      const elapsed = prev[nextMsg.id] ? Math.floor((Date.now() - startTime) / 1000) : 3
      return {
        ...prev,
        [nextMsg.id]: { elapsed: Math.max(elapsed, 1), completed: true }
      }
    })

    // 3. Collapse tasks panel, hide "Thinking..." shimmer and start streaming response text
    setOpenStates((prev) => ({ ...prev, [`${nextMsg.id}-tasks`]: false }))

    const words = nextMsg.content.split(" ")
    let textBuffer = ""

    for (let i = 0; i < words.length; i++) {
      textBuffer += (i === 0 ? "" : " ") + words[i]
      setCurrentStreamingText(textBuffer)
      setMessages((prev) =>
        prev.map((m) => (m.id === nextMsg.id ? { ...m, content: textBuffer } : m))
      )
      // Stream speed: 40ms per word
      await new Promise((resolve) => setTimeout(resolve, 40))
    }

    // 4. Stream Sources citation card (at the very end)
    if (nextMsg.sources && nextMsg.sources.length > 0) {
      setMessages((prev) =>
        prev.map((m) => (m.id === nextMsg.id ? { ...m, sources: nextMsg.sources } : m))
      )
      setOpenStates((prev) => ({ ...prev, [`${nextMsg.id}-sources`]: false })) // collapse sources by default
    }

    // 5. Render canvas trigger card (at the very end)
    if (nextMsg.canvasContent) {
      setMessages((prev) =>
        prev.map((m) => (m.id === nextMsg.id ? { ...m, canvasContent: nextMsg.canvasContent } : m))
      )
    }

    // 6. Append elicitation if present (simulating pausing the stream for human response)
    if (nextMsg.elicitation) {
      setMessages((prev) =>
        prev.map((m) => (m.id === nextMsg.id ? { ...m, elicitation: nextMsg.elicitation } : m))
      )
    }

    // 7. Streaming completes
    setIsStreaming(false)
    setStreamingMessageId(null)
    setCurrentStreamingText("")
    setPlaybackIndex((prev) => prev + 1)

    // 8. Slide open the canvas side panel (after text finishes with a smooth delay)
    if (nextMsg.canvasContent) {
      await new Promise((resolve) => setTimeout(resolve, 400))
      setActiveCanvasContent(nextMsg.canvasContent)
      setCanvaOpen(true)
    }
  }

  // Auto play the scenario (only if not interrupted by a pending elicitation)
  React.useEffect(() => {
    let timeout: any
    const hasUnresolvedElicitation = messages.some((msg) => msg.elicitation && !msg.elicitation.resolved)

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
  }, [playbackIndex, isStreaming, messages, activeScenario])

  // Resolve an elicitation
  const handleResolveElicitation = async (messageId: string, optionLabel: string) => {
    // 1. Mark elicitation as resolved in messages state
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId && msg.elicitation
          ? { ...msg, elicitation: { ...msg.elicitation, resolved: true, selectedOption: optionLabel } }
          : msg
      )
    )

    // 2. Append user response bubble reflecting the decision
    const userMsgId = `user-decision-${Date.now()}`
    const userMsg: MockMessage = {
      id: userMsgId,
      role: "user",
      senderName: userRole === "complete" ? "Professor Allan" : "Student Allan",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: `${optionLabel}`
    }

    setMessages((prev) => [...prev, userMsg])

    // 3. Trigger simulated response completion
    setIsStreaming(true)
    const followUpMsgId = `assistant-followup-${Date.now()}`

    let content = ""
    let tasks: any[] = []
    let canvasContent: any = null

    if (selectedScenarioId === "batch-grade") {
      content = "Understood — applying provisional grades. I have generated the audited semester report PDF for s_012, s_019, s_024, and s_031. Outliers have been logged successfully [1]."
      tasks = [
        { title: "write_file(\"semester_report_final.pdf\")", state: "completed" as const, description: "Generating final semester performance PDF." }
      ]
      canvasContent = {
        title: "Semester Performance Report Summary",
        type: "PDF · Document",
        visualType: "code",
        code: `FAIR Grading Audit Report - HW3
Status: Audited
Decided Action: Provisional Grades Accepted
Flagged Items: 4 (Handwriting thresholds resolved)
Median Class Score: 74/100`
      }
    } else {
      content = `Got it — adding the knowledge component 'applying chain rule to implicit functions incorrectly' to the Calc_V2 taxonomy ledger [1].`
      tasks = [
        { title: "write_file(\"calc_v2_taxonomy.json\")", state: "completed" as const, description: "Rebuilding taxonomy node hierarchy." }
      ]
    }

    setMessages((prev) => [
      ...prev,
      {
        id: followUpMsgId,
        role: "assistant",
        senderName: "Fair Co-pilot",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: "",
        tasks: []
      }
    ])

    // TTT delay
    await new Promise((resolve) => setTimeout(resolve, 600))

    // Run task timer
    const startTime = Date.now()
    setTaskTimers((prev) => ({
      ...prev,
      [followUpMsgId]: { elapsed: 0, completed: false }
    }))

    const timerInterval = setInterval(() => {
      setTaskTimers((prev) => {
        const current = prev[followUpMsgId]
        if (!current || current.completed) {
          clearInterval(timerInterval)
          return prev
        }
        return {
          ...prev,
          [followUpMsgId]: { ...current, elapsed: Math.floor((Date.now() - startTime) / 1000) }
        }
      })
    }, 100)

    setMessages((prev) =>
      prev.map((m) => (m.id === followUpMsgId ? { ...m, tasks: [{ ...tasks[0], state: "running" as const }] } : m))
    )
    setOpenStates((prev) => ({ ...prev, [`${followUpMsgId}-tasks`]: true }))

    await new Promise((resolve) => setTimeout(resolve, 1200))

    setMessages((prev) =>
      prev.map((m) => (m.id === followUpMsgId ? { ...m, tasks: tasks } : m))
    )
    setTaskTimers((prev) => ({
      ...prev,
      [followUpMsgId]: { elapsed: 1, completed: true }
    }))
    setOpenStates((prev) => ({ ...prev, [`${followUpMsgId}-tasks`]: false }))

    // Stream text
    const words = content.split(" ")
    let textBuffer = ""
    for (let i = 0; i < words.length; i++) {
      textBuffer += (i === 0 ? "" : " ") + words[i]
      setMessages((prev) =>
        prev.map((m) => (m.id === followUpMsgId ? { ...m, content: textBuffer } : m))
      )
      await new Promise((resolve) => setTimeout(resolve, 40))
    }

    // Append mock sources
    const finalSources = [
      { index: 1, title: "Calculus KC Mapping Registry", snippet: "Registry entries updated with decision nodes.", type: "doc" as const }
    ]
    setMessages((prev) =>
      prev.map((m) => (m.id === followUpMsgId ? { ...m, sources: finalSources, canvasContent } : m))
    )

    setIsStreaming(false)
    setStreamingMessageId(null)

    if (canvasContent) {
      await new Promise((resolve) => setTimeout(resolve, 300))
      setActiveCanvasContent(canvasContent)
    }
  }

  const simulateGenericResponse = async () => {
    setIsStreaming(true)
    const agentMsgId = `agent-${Date.now()}`
    const responseText = "I have updated the analysis model. Let's inspect the results [1]. Let me know if you would like me to compile another calculation [2]."

    setMessages((prev) => [
      ...prev,
      {
        id: agentMsgId,
        role: "assistant",
        senderName: "Fair Co-pilot",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: "",
        tasks: [],
      }
    ])

    // Simulated TTT delay: 200ms - 1200ms before working panel appears
    const tttDelay = 200 + Math.floor(Math.random() * 1000)
    await new Promise((resolve) => setTimeout(resolve, tttDelay))

    setOpenStates((prev) => ({
      ...prev,
      [`${agentMsgId}-tasks`]: true,
      [`${agentMsgId}-sources`]: false,
    }))

    // Initialize timer tracking
    const startTime = Date.now()
    setTaskTimers((prev) => ({
      ...prev,
      [agentMsgId]: { elapsed: 0, completed: false }
    }))

    const timerInterval = setInterval(() => {
      setTaskTimers((prev) => {
        const current = prev[agentMsgId]
        if (!current || current.completed) {
          clearInterval(timerInterval)
          return prev
        }
        return {
          ...prev,
          [agentMsgId]: { ...current, elapsed: Math.floor((Date.now() - startTime) / 1000) }
        }
      })
    }, 100)

    // Simulate steps running
    const steps = [
      { title: "read_file(\"diagnostic_schema.json\")", state: "completed" as const },
      { title: "exec(\"python run_compilation.py\")", state: "completed" as const }
    ]

    const currentTasks: any[] = []
    for (let i = 0; i < steps.length; i++) {
      currentTasks.push({ ...steps[i], state: "running" as const })
      setMessages((prev) =>
        prev.map((m) => (m.id === agentMsgId ? { ...m, tasks: [...currentTasks] } : m))
      )
      await new Promise((resolve) => setTimeout(resolve, 1000))

      currentTasks[i] = steps[i]
      setMessages((prev) =>
        prev.map((m) => (m.id === agentMsgId ? { ...m, tasks: [...currentTasks] } : m))
      )
    }

    // Stop timer
    setTaskTimers((prev) => {
      const elapsed = prev[agentMsgId] ? Math.floor((Date.now() - startTime) / 1000) : 2
      return {
        ...prev,
        [agentMsgId]: { elapsed: Math.max(elapsed, 1), completed: true }
      }
    })

    setOpenStates((prev) => ({ ...prev, [`${agentMsgId}-tasks`]: false }))

    // Stream text
    const words = responseText.split(" ")
    let textBuffer = ""

    for (let i = 0; i < words.length; i++) {
      textBuffer += (i === 0 ? "" : " ") + words[i]
      setMessages((prev) =>
        prev.map((m) => (m.id === agentMsgId ? { ...m, content: textBuffer } : m))
      )
      await new Promise((resolve) => setTimeout(resolve, 40))
    }

    // Add sources
    const finalSources = [
      { index: 1, title: "Diagnostic Schema Metadata", snippet: "Main specification mapping metrics to grading rules.", type: "file" as const },
      { index: 2, title: "Model Run Log", snippet: "Logs of local testing iterations.", type: "doc" as const }
    ]

    setMessages((prev) =>
      prev.map((m) => (m.id === agentMsgId ? { ...m, sources: finalSources } : m))
    )
    setOpenStates((prev) => ({ ...prev, [`${agentMsgId}-sources`]: false }))

    setIsStreaming(false)
    setStreamingMessageId(null)
  }

  // Handle manual message send wrapper
  const handleSend = (inputValue: string, uploadedFiles: any[]) => {
    if (!inputValue.trim() && uploadedFiles.length === 0) return

    const newMsg: MockMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      senderName: "Allan",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: inputValue,
      attachments: uploadedFiles.map(f => ({ ...f, isImage: false })),
    }

    setMessages((prev) => [...prev, newMsg])

    // Simulate generic agent response after a short delay
    setTimeout(() => {
      simulateGenericResponse()
    }, 1000)
  }

  return {
    userRole,
    setUserRole,
    selectedScenarioId,
    setSelectedScenarioId,
    activeScenario,
    messages,
    setMessages,
    isStreaming,
    playbackIndex,
    canvaOpen,
    setCanvaOpen,
    activeCanvasContent,
    setActiveCanvasContent,
    openStates,
    setOpenStates,
    taskTimers,
    personaLoaded,
    setPersonaLoaded,
    streamingMessageId,
    resetSimulation,
    playNextTurn,
    handleResolveElicitation,
    handleSend
  }
}

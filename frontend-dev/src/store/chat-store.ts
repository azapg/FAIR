import { create } from "zustand"

export type AgentState = "idle" | "thinking" | "working" | "waiting_for_user"

export type ToolCategory =
  | "data_read"
  | "web_search"
  | "validation"
  | "calendar"
  | "file_inspect"
  | "code_execution"
  | "grading"
  | "delegation"
  | "communication";

export type EventStatus = "running" | "completed" | "failed" | "error" | "awaiting_input";

export type ChatEventBlock = 
  | { type: "text", content: string, id?: string, timestamp?: string, playbackDelayMs?: number }
  | { type: "thought", content: string, durationMs?: number, id?: string, timestamp?: string, playbackDelayMs?: number }
  | { type: "tool_call", toolName: string, args?: any, status: EventStatus, resultSummary?: string, result?: unknown, category?: ToolCategory, label?: string, id?: string, timestamp?: string, playbackDelayMs?: number, parentId?: string }
  | { type: "artifact_update", action?: "create" | "edit" | "delete", artifactName?: string, diff?: { added: number, removed: number }, content?: string, result?: unknown, id?: string, timestamp?: string, playbackDelayMs?: number }
  | { type: "interrupt", content: string, status?: EventStatus, id?: string, timestamp?: string, playbackDelayMs?: number }
  | { type: "status_pulse", content: string, id?: string, timestamp?: string, playbackDelayMs?: number }

export interface CanvasPayload {
  title: string
  type: string
  visualType: "chart" | "simulation" | "code"
  code?: string
  data?: any
}

export interface ElicitationPayload {
  id: string
  questions: {
    id: string
    title: string
    options: { label: string; value: string }[]
  }[]
  resolved?: boolean
  selectedOption?: string
}

export interface SourcePayload {
  index: number
  title: string
  url?: string
  snippet?: string
  type?: "web" | "file" | "doc"
}

export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  senderName: string
  timestamp: string
  content: string // Accumulated text content for backwards compatibility
  
  // The raw sequence of events from the agent in order
  events?: ChatEventBlock[]
  
  attachments?: {
    name: string
    size: string
    type: string
    isImage?: boolean
    src?: string
  }[]
  
  elicitation?: ElicitationPayload
  sources?: SourcePayload[]
  canvasContent?: CanvasPayload
  
  statusPulse?: {
    message: string
    elapsed: string
  }
}

// ---------------------------
// Slices
// ---------------------------

interface MessageSlice {
  messages: Message[]
  streamingMessageId: string | null
  agentState: AgentState
  appendMessage: (msg: Message) => void
  updateMessage: (id: string, partial: Partial<Message>) => void
  addMessageEvent: (id: string, event: ChatEventBlock) => void
  updateLastMessageEvent: (id: string, updater: (event: ChatEventBlock) => ChatEventBlock) => void
  clearChat: () => void
  setMessages: (messages: Message[]) => void
  setAgentState: (state: AgentState) => void
  setStreamingMessageId: (id: string | null) => void
}

interface ElicitationSlice {
  activeElicitation: ElicitationPayload | null
  setActiveElicitation: (e: ElicitationPayload | null) => void
}

interface LayoutSlice {
  isCanvasOpen: boolean
  activeCanvasContent: CanvasPayload | null
  activeSourcesMessageId: string | null
  selectedModel: string
  greetingMessage: string
  setCanvasOpen: (open: boolean) => void
  setActiveCanvasContent: (payload: CanvasPayload | null) => void
  setActiveSourcesMessageId: (id: string | null) => void
  setSelectedModel: (model: string) => void
  setGreetingMessage: (msg: string) => void
}

interface InputSlice {
  inputValue: string
  attachments: any[] // Mocked files
  isWebSearchEnabled: boolean
  selectedCourse: string | null
  setInputValue: (val: string) => void
  setIsWebSearchEnabled: (enabled: boolean) => void
  setSelectedCourse: (course: string | null) => void
  setAttachments: (files: any[]) => void
}

export type ChatStore = MessageSlice & ElicitationSlice & LayoutSlice & InputSlice

export const useChatStore = create<ChatStore>()((set) => ({
  // --- Message Slice ---
  messages: [],
  streamingMessageId: null,
  agentState: "idle",
  appendMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  updateMessage: (id, partial) => set((state) => ({
    messages: state.messages.map(m => m.id === id ? { ...m, ...partial } : m)
  })),
  addMessageEvent: (id, event) => set((state) => ({
    messages: state.messages.map(m => {
      if (m.id !== id) return m
      return { ...m, events: [...(m.events || []), event] }
    })
  })),
  updateLastMessageEvent: (id, updater) => set((state) => ({
    messages: state.messages.map(m => {
      if (m.id !== id || !m.events || m.events.length === 0) return m
      const newEvents = [...m.events]
      newEvents[newEvents.length - 1] = updater(newEvents[newEvents.length - 1])
      return { ...m, events: newEvents }
    })
  })),
  clearChat: () => set({ messages: [], streamingMessageId: null, agentState: "idle" }),
  setMessages: (messages) => set({ messages }),
  setAgentState: (s) => set({ agentState: s }),
  setStreamingMessageId: (id) => set({ streamingMessageId: id }),

  // --- Elicitation Slice ---
  activeElicitation: null,
  setActiveElicitation: (e) => set({ activeElicitation: e }),

  // --- Layout Slice ---
  isCanvasOpen: false,
  activeCanvasContent: null,
  activeSourcesMessageId: null,
  selectedModel: "feynman",
  greetingMessage: "How can I help, Allan?",
  setCanvasOpen: (open) => set({ isCanvasOpen: open }),
  setActiveCanvasContent: (content) => set({ activeCanvasContent: content }),
  setActiveSourcesMessageId: (id) => set({ activeSourcesMessageId: id }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  setGreetingMessage: (msg) => set({ greetingMessage: msg }),

  // --- Input Slice ---
  inputValue: "",
  attachments: [],
  isWebSearchEnabled: true,
  selectedCourse: null,
  setInputValue: (val) => set({ inputValue: val }),
  setIsWebSearchEnabled: (enabled) => set({ isWebSearchEnabled: enabled }),
  setSelectedCourse: (course) => set({ selectedCourse: course }),
  setAttachments: (files) => set({ attachments: files }),
}))

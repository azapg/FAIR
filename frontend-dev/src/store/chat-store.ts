import { create } from "zustand"
import type {
  AgentState,
  CanvasPayload,
  ChatEventBlock,
  ElicitationPayload,
  Message,
} from "@/lib/chat-contract"
export type {
  AgentState,
  CanvasPayload,
  ChatEventBlock,
  ElicitationPayload,
  EventStatus,
  Message,
  SourcePayload,
  ToolCategory,
} from "@/lib/chat-contract"

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

export type AgentState = "idle" | "thinking" | "working" | "waiting_for_user";

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
  | { type: "text"; content: string; id?: string; timestamp?: string; playbackDelayMs?: number }
  | { type: "thought"; content: string; durationMs?: number; id?: string; timestamp?: string; playbackDelayMs?: number }
  | { type: "tool_call"; toolName: string; args?: any; status: EventStatus; resultSummary?: string; result?: unknown; category?: ToolCategory; label?: string; id?: string; timestamp?: string; playbackDelayMs?: number; parentId?: string }
  | { type: "artifact_update"; action?: "create" | "edit" | "delete"; artifactName?: string; diff?: { added: number; removed: number }; content?: string; result?: unknown; id?: string; timestamp?: string; playbackDelayMs?: number }
  | { type: "interrupt"; content: string; status?: EventStatus; id?: string; timestamp?: string; playbackDelayMs?: number }
  | { type: "status_pulse"; content: string; id?: string; timestamp?: string; playbackDelayMs?: number };

export interface CanvasPayload {
  title: string;
  type: string;
  visualType: "chart" | "simulation" | "code";
  code?: string;
  data?: any;
}

export interface ElicitationPayload {
  id: string;
  questions: {
    id: string;
    title: string;
    options: { label: string; value: string }[];
  }[];
  resolved?: boolean;
  selectedOption?: string;
}

export interface SourcePayload {
  index: number;
  title: string;
  url?: string;
  snippet?: string;
  type?: "web" | "file" | "doc";
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  senderName: string;
  timestamp: string;
  content: string;
  events?: ChatEventBlock[];
  attachments?: {
    name: string;
    size: string;
    type: string;
    isImage?: boolean;
    src?: string;
  }[];
  elicitation?: ElicitationPayload;
  sources?: SourcePayload[];
  canvasContent?: CanvasPayload;
  statusPulse?: {
    message: string;
    elapsed: string;
  };
}

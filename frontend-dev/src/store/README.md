# Fair Platform Chat UI State Management

This directory contains the unified state store (`chat-store.ts`) for the FAIR platform chat UI. 

## Architecture Overview
We use **Zustand** combined with the **Slice Pattern** to manage the complexity of rendering multi-hour autonomous agents and simple 1-shot chatbots interchangeably.

Instead of managing one massive state object, the state is divided into logical slices inside `chat-store.ts`:
- **`MessageSlice`**: Core conversation data (messages, event streams, agent states).
- **`ElicitationSlice`**: Interactive interrupts and questions for the user.
- **`LayoutSlice`**: UI panels (Canvas, Sources, sidebars).
- **`InputSlice`**: User input area.

## The Event Protocol
Agents in the FAIR Platform stream raw events to the UI instead of grouping things explicitly by "Tasks". The `Message` schema holds an `events` array of `ChatEventBlock`.

### Example Agent Event Loop
1. Agent starts reasoning:
   `{ type: "thought", content: "Let's check the fair CLI help..." }`
2. Agent calls a tool:
   `{ type: "tool_call", toolName: "run_command", args: "git status", status: "completed" }`
3. Agent outputs text to the user:
   `{ type: "text", content: "I've checked the repository and we are on the chat branch." }`

### UI Rendering Philosophy
The UI is responsible for intelligently aggregating these events. When rendering `chat-message.tsx`:
- Any `thought` or `tool_call` blocks that appear **before** a `text` block are dynamically grouped into a collapsible **"Worked for Xs"** UI wrapper.
- `artifact_update` events are rendered as rich inline cards inside the event stream.
- `canvas_widget` payloads (or complex custom HTML) escalate directly to the `ChatCanvas` side panel.

## Agent States

The FAIR frontend explicitly models the agent's real-time state using a strict enum to drive UI shimmering, disable inputs, and control the auto-scroll behaviors.
```typescript
export type AgentState = "idle" | "thinking" | "working" | "waiting_for_user"
```
- `idle`: The system is waiting for the user to submit a prompt.
- `thinking`: The system acknowledged a request but hasn't received tool calls or text yet (initial spinner).
- `working`: The system is actively executing tools, generating thoughts, or streaming text tokens to the UI.
- `waiting_for_user`: The system pauses execution to prompt the user for an explicit decision (via an inline Elicitation widget).

## Advanced Payloads

Messages are not just text. They can contain rich interactive payloads:
- **`CanvasPayload`**: Automatically triggers the Open Canvas sliding pane for interactive data visualizations (`chart`), sandbox executions (`simulation`), or rich markdown documents (`code`).
- **`ElicitationPayload`**: Appends interactive Multiple-Choice Questions (MCQ) directly below a message, allowing agents to pause execution and request human-in-the-loop decisions (e.g., grading edge-cases).
- **`statusPulse`**: Renders a floating, pulse-animated status chip (e.g., "Synthesizing 4,000 files") at the bottom of the chat to keep the user informed during long background tasks without emitting persistent chat events.

## Test System Panel & Simulation

In a development environment, the backend is not always available. The UI provides a powerful `ChatSidebar` (Test System Panel) and `useScenarioPlayback` hook:
- You can inject mock `Message` objects into the store dynamically to test new payloads.
- **Simulation**: Instead of appending raw messages instantly, `useScenarioPlayback.simulateMessage()` parses injected events, applies artificial `setTimeout` delays, and orchestrates the `AgentState` (`working` -> `idle`) to perfectly replicate the experience of watching an agent reason and type in real-time.

## Usage
Simply import `useChatStore` in your components:
```tsx
import { useChatStore } from "@/store/chat-store"

function MyComponent() {
  const inputValue = useChatStore((state) => state.inputValue)
  const setInputValue = useChatStore((state) => state.setInputValue)
  // ...
}
```

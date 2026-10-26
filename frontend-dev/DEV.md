# FAIR Chat Test System Architecture

This document serves as a technical and architectural guide to the **Chat Test System** (also known as the Test System Panel) built into the FAIR Platform frontend. It explains how developers and agents can inject state, simulate behaviors, and contribute to this debugging UI.

## 1. System Overview

The core philosophy of the Chat Test System is that **the UI is entirely driven by a global Zustand store** (`useChatStore`). There is no real backend connection required to test the UI. Every visual element—from chat bubbles and shimmer effects to complex Open Canvas widgets—is rendered purely based on the data in the store.

By manipulating `useChatStore`, we can simulate complex agent behaviors, edge cases, and dynamic UI adaptations.

## 2. The Test System Panel (`ChatSidebar.tsx`)

The `ChatSidebar` is the primary control center for the debugging UI. It features three tabs:
- **Scenarios**: Allows users to load predefined mock chats (e.g., Data Viz, Orchestration). Selecting a scenario instantly hydrates the store and can trigger automated playback.
- **Debug (State Editor)**: Provides deep control over the current chat state. Includes the `AgentState` override, the Message List Manager, and the advanced "Create Custom Message" sheet.
- **Settings**: Allows toggling the UI layout mode (e.g., `simplified` vs `complete` role views).

### The "Create Custom Message" Sheet

This is the ultimate state injection tool. It dynamically expands to allow developers to sculpt and append a custom `Message` object with surgical precision:
- **Core Metadata**: `Role` (User, Assistant, System), `Sender Name`, and `Timestamp`.
- **Mock Add-ons**: Expanding cards that dynamically reveal input fields for various payloads:
  - **Mock Events**: Define custom arrays of `thought` and `tool_call` blocks.
  - **Elicitation**: Construct interactive multiple-choice widgets inline.
  - **Attachments**: Inject mock files (with custom names, sizes, and types) into the message bubble.
  - **Canvas Payload**: Supply a title and visual type (`chart`, `simulation`, `code`) to render the Open Canvas wrapper right next to the chat log.

### Simulation Toggle

When injecting a custom message via the sheet, a toggle labeled **"Simulate animation delays & streams"** allows developers to bypass instant appending. If enabled, the `ChatSidebar` routes the payload through `simulateMessage()`, artificially introducing typing delays and state transitions for a realistic UX test.

## 3. The Playback Hook (`use-scenario-playback.ts`)

This hook acts as the "director" of the simulation. It reads the static `mockScenarios` and translates them into a dynamic, time-based sequence of store updates.

### Key Functions
- **`playNextTurn`**: Advances the scenario sequence. It takes the next full message object, injects a blank shell into the store, and artificially streams the events and text over time using `setTimeout` loops.
- **`simulateMessage`**: An exported utility function (used by the custom message sheet) that takes any fully formed `Message` object and applies the exact same streaming delay logic as `playNextTurn`.
- **`handleResolveElicitation`**: Simulates the agent's response when a user selects an option in an Elicitation widget. It prevents automatic mocking if the active scenario is set to `"none"`.

### Handling Agent States
The playback hook tightly orchestrates the `AgentState` enum (`idle`, `thinking`, `working`, `waiting_for_user`).
- While processing tool calls and thoughts, the state is `"working"`.
- While streaming text, the state remains `"working"` (to prevent the UI from prematurely signaling completion).
- Once the text and payload (Canvas, Elicitation) are fully rendered, it transitions to `"idle"` or `"waiting_for_user"`.

## 4. Contributing

When adding new features or visual payloads to the chat interface:
1. **Define the Types**: Add your new payload type to `Message` in `chat-store.ts`.
2. **Build the Mock Builder**: Update the "Create Custom Message" sheet in `ChatSidebar.tsx` to include dynamic inputs for your payload.
3. **Handle Simulation**: Ensure that `playNextTurn` and `simulateMessage` in `use-scenario-playback.ts` properly sequence the rendering of your payload (e.g., adding arbitrary `setTimeout` delays if necessary for realism).

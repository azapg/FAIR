# FAIR Chat UI & Agent Orchestration System

This folder contains the core implementation of the long-running agent orchestration and chat interface for **The Fair Platform (FAIR)**.

---

## 1. Overview & Architecture

Unlike generic chatbots, the FAIR Chat UI acts as an orchestration surface for complex, multi-minute reasoning tasks (e.g., batch grading runs, clustering diagnostic test scores, generating slide decks and physics simulations).

The system aligns with the **FAIR Conversation Taxonomy** and utilizes:
- **Core Chat Stack:** Custom Vercel AI SDK elements (`MessageScroller`, `Message`, `Bubble`, `Attachment`, `Marker`).
- **Interactive Checklists & Sources:** Collapsible task logs (`Task`, `TaskTrigger`, `TaskContent`, `TaskItem`) and citations (`Sources`, `SourcesTrigger`, `SourcesContent`, `Source`, `InlineCitation`).
- **Dynamic Animations:** WebGL Rive-based interactive blobs (`Persona`) for agent states.
- **Canva (Side Panel):** Split-view layouts to render interactive visualizations (SVG regional graphs, canvas double pendulums, syntax code blocks).

---

## 2. Rendering Taxonomy & Event Model

The interface is driven by a structured state model designed to represent incremental agent heartbeats:

1. **Human Turn:** Renders text content, voice speech-to-text indicators, and attached files (e.g., `.csv`, `.json`, `.png`) in uniform capsules.
2. **TTT (Time-to-First-Token) Phase:** Shows an animation of the Opal `Persona` (in its `idle` state) next to a clean, gradient-swept `"Thinking..."` text. No task headers or content bubbles are visible during this latency delay.
3. **Working Phase:** Displays a collapsible `Task` trigger containing a live, counting work timer: `Working... (Xs)`. Tool calls (`read_file`, `write_file`, `exec`) render as clean list items displaying neutral Lucide action icons.
4. **Status Heartbeat Pulse:** If the backend streams status heartbeats, a secondary indicator (e.g. `"Working — 24 of 32 submissions graded"`) prints directly inside the task trigger.
5. **Generative Artifacts:** Streamed inline as they complete, rendering preview templates or direct click-to-open links that slide open the Canva.
6. **Auto-Collapse & Final Response:** Once streaming terminates, completed reasoning checklist steps and sources automatically collapse so the user can focus on the response. The user can expand them manually.

---

## 3. Human-in-the-Loop Interrupts

When sub-agents encounter thresholds or ambiguous rubrics, they stream an `interrupt` block containing a prompt and choice options:

- **Input Lockout:** The chat input area is disabled, changing its placeholder to `"Awaiting decision above..."` to simulate server-side execution pauses.
- **Visual Card:** Renders a prominent card in the message thread (`border-amber-500/50 bg-amber-500/5`).
- **Resolution Flow:** Clicking an option:
  1. Sets `resolved: true` and logs the choice inside the message history.
  2. Appends a user bubble showing the selection.
  3. Resumes the orchestrator stream to run succeeding compilation tasks.

---

## 4. Role-Differentiated Views

The dashboard features a **Select UI Role View** to switch layout presentation behaviors dynamically:

- **Student:** Focuses on concept explanations. Checklist tasks default to collapsed. Decision interrupts are replaced with a non-interactive message: `"Awaiting instructor approval to continue..."`.
- **Professor:** Focuses on validation. Displays live execution steps, heartbeats, and allows resolving decision interrupts.
- **Researcher:** Focuses on raw verification. Checklist tasks are forced open permanently, and every task step exposes a **JSON** link that opens an alert window with the raw parameters.

---

## 5. Visual Styling & Animations

- **Text Shimmer:** Custom `@keyframes shine` translation sweeps a linear gradient across the text mask in [globals.css](file:///c:/Users/allan/Documents/fair-platform/frontend-dev/src/globals.css) (supporting light/dark themes).
- **Fade-in Rive Persona:** To prevent blank layout shifts while Rive compiles WebGL context assets from URLs, we track ready states using `onLoad`. The Persona is initially collapsed (`opacity-0 w-0 h-0`) and transitions smoothly (`transition-all duration-300`) to `opacity-100 size-6` on ready.
- **Neutral Tool Icons:** All active tool items use neutral `text-muted-foreground/80` coloring to prevent visual clutter.

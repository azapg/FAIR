---
title: SDK Overview
description: Extend Fair Platform by building plugins for transcribing, grading, validation, and storage.
---

Fair Platform is designed to be **extensible**. The SDK is the layer that lets you add custom behavior—without forking the core platform—by implementing *plugins* that the backend can discover, configure, and run.

Use the SDK when you want to:

- Add new **interpreters/transcribers** (turn submissions like PDFs, images, notebooks, ZIPs into standardized artifacts)
- Add new **graders** (rubric-based, LLM-based, hybrid, agentic workflows)
- Add new **validators** (e.g., format checks, plagiarism checks, compile checks, proof verification)
- Add custom **storage backends** (for artifacts, results, datasets, etc.)

---

## How the SDK fits into the platform

At a high level:

1. A **student** uploads a submission to an assignment.
2. Fair Platform stores it and creates one or more **artifacts**.
3. Optional **transcriber/interpreter plugins** process raw uploads into normalized artifacts (OCR, parsing, extraction, execution logs, etc.).
4. **grader plugins** evaluate artifacts and produce grades + feedback.
5. **validator plugins** can enforce constraints or add flags/warnings.
6. The backend exposes results via the API and UI.

This architecture is meant to support experimentation: you can swap modules, compare approaches, and keep experiments reproducible.

---

## Core concepts

### Plugins
A *plugin* is a unit of extension that the platform can:

- Discover at startup
- Validate configuration for
- Run as part of a workflow

Plugins typically have:

- A unique identifier / name
- A type (grader, transcriber/interpreter, validator, storage, etc.)
- A **settings** schema so the UI/API can configure it safely

### Artifacts
Artifacts are the platform’s internal “standard form” for student work and derived data.

Artifacts can represent:

- Original uploaded files (PDF, images, ZIPs)
- Extracted text (OCR output)
- Parsed notebook cells
- Code execution logs
- Structured extracted data

Plugins should generally **consume artifacts and produce artifacts + metadata**.

### Assignments, submissions, and results
- **Assignments** define what students submit, accepted formats, and evaluation rules.
- **Submissions** contain uploaded content (and derived artifacts).
- **Results** contain grades, feedback, and any additional outputs.

---

## Plugin configuration (settings)

A key SDK feature is **typed settings**.

Instead of accepting arbitrary dictionaries, plugins define configuration fields so:

- The backend can validate config on save
- The UI can render forms dynamically
- Experiments can be exported/imported consistently

Examples of things that commonly become plugin settings:

- Rubric text or rubric file reference
- LLM provider/model name (and whether streaming is enabled)
- Temperature / max tokens
- Allowed file types and size limits
- Grading thresholds
- Whether to run in “strict” mode

Security note: any external service (LLMs, storage, etc.) should use **environment variables** or secret management for API keys—do not hardcode secrets into plugin settings.

---

## Typical development workflow

1. **Run the platform in dev mode** so the UI and API are easy to iterate on.
2. Implement your plugin class using the SDK base classes.
3. Register/expose the plugin so it can be discovered by the backend’s plugin loader.
4. Start the server and verify the plugin appears in the UI.
5. Create an assignment/course that uses your plugin.
6. Submit test work and validate outputs.

If you’re doing frontend development, the platform supports a split workflow:

- Frontend dev server for UI iteration
- Backend dev server for API/plugin iteration

---

## Quality and reproducibility guidelines

When building plugins intended for research or repeated use:

- Prefer **deterministic outputs** where possible (or log randomness seeds/parameters).
- Store inputs/outputs as artifacts so runs can be audited.
- Add clear versioning and changelogs for plugin behavior changes.
- Avoid hidden state; make configuration explicit via settings.

---

## Next pages

- `sdk/plugins`: Plugin types and recommended structure
- `sdk/schemas`: Data models you’ll interact with (Submission, Assignment, Artifact, etc.)
- `sdk/examples`: Small examples (starter plugins you can copy)

If you tell me which plugin you want to build first (OCR transcriber, rubric grader, code runner, etc.), I can draft an example plugin skeleton consistent with Fair Platform’s SDK structure.
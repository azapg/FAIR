---
title: Plugins (Guide)
description: Learn how to develop, package, and run Fair Platform plugins (graders, transcribers/interpreters, validators, and storage).
---

This guide is for **developers** who want to extend Fair Platform by building **plugins**.

> Status: This page is intentionally a **starter / placeholder** so it doesn’t 404 while we expand the full plugin documentation. It already reflects the intended architecture and workflow.

## What is a plugin in Fair Platform?

A **plugin** is an extension module that Fair Platform can:

- **discover** at startup
- **validate configuration** for (via a typed settings schema)
- **execute** as part of the platform workflow (processing submissions/artifacts, grading, validating, etc.)

Plugins are the primary way to add new capabilities without forking the core platform.

## Common plugin categories

Fair Platform’s plugin ecosystem is designed around the grading pipeline and the artifact model.

### Transcribers / Interpreters
These plugins normalize raw submissions into structured, consistent **artifacts**.

Examples:
- OCR text from photos of handwritten work
- Extracted text from PDFs
- Parsed code/notebook content
- Extracted answers from a form submission

### Graders
These plugins produce grades and feedback.

Examples:
- Rubric-based graders (deterministic)
- LLM-based graders (configurable temperature/model)
- Hybrid graders (rubric + LLM critique)
- Agentic graders (multi-step reasoning/workflows)

### Validators
These plugins enforce constraints or surface quality issues.

Examples:
- File format checks (must include X, must be PDF)
- Compilation/execution checks for code assignments
- Policy/academic integrity checks
- Proof/solution verification for formal work

### Storage backends
These plugins change or augment where artifacts/results are stored and retrieved.

Examples:
- Store artifacts in S3-compatible object storage
- Store datasets in a custom backend
- Add mirroring or retention policies

## How plugins fit into the workflow

A typical Fair workflow looks like:

1. A student uploads a submission
2. Fair stores it and creates one or more **artifacts**
3. Transcriber/interpreter plugins may produce derived artifacts (OCR, parsed output, etc.)
4. A grader plugin evaluates artifacts and produces grades + feedback
5. Validators may add warnings/flags or block acceptance
6. Results are served via API and UI

Key idea: plugins should generally **consume artifacts and produce artifacts + results**, not operate on raw files ad-hoc.

## Configuration: typed settings

One of the most important requirements in Fair Platform is that plugin configuration is **typed** (schema-driven), because it enables:

- safe validation in the backend
- dynamic forms in the frontend UI
- reproducibility (configs can be exported/imported)
- clearer research results (exact parameters are captured)

Examples of typical settings fields:
- rubric text / rubric file reference
- enabled flags and thresholds
- model provider + model name (for LLM graders)
- temperature / max tokens
- strict mode / acceptance criteria
- file type allowlists
- timeouts for external tools

### Security note (important)
Do not store secrets (API keys, tokens) in plugin settings. Use environment variables or a secrets manager. Settings should be safe to serialize and share with experiments.

## Development workflow (recommended)

This is the usual loop for building a plugin:

1. Run the backend in a development-friendly mode
2. Implement the plugin (code + settings schema)
3. Ensure the plugin is discoverable by the backend loader
4. Start the platform and verify the plugin appears in the UI
5. Create a course/assignment that uses the plugin
6. Submit test work; validate artifacts/results
7. Iterate (logs, traces, reproducibility)

### Backend + frontend dev split (fast UI iteration)

- Backend dev server:
  - `uv run fair serve --dev --port 8000`
- Frontend dev server:
  - `cd frontend-dev && bun install && bun run dev`

This gives you fast frontend reload while still running the real backend plugin loader.

## Packaging and discovery (placeholder)

This section will be expanded to the precise project conventions. The intent is:

- Plugins should be discoverable automatically (or via explicit registration)
- Plugins should declare:
  - identity (name/id)
  - type (grader/transcriber/validator/storage)
  - settings schema
- Plugins should be versioned and documented to support reproducible experiments

## Testing suggestions (practical)

Even before full e2e tests exist, you’ll usually want:

- Unit tests for pure transformation logic
- Golden-file tests for deterministic artifact generation
- Smoke tests that load the plugin and run it through a minimal submission
- A “known inputs → expected outputs” fixture directory (especially for research)

## Troubleshooting (placeholder)

Common issues you might hit:

- Plugin not showing up in UI:
  - plugin loader didn’t discover it (registration/packaging issue)
- Plugin runs but outputs don’t appear:
  - artifact/result isn’t being persisted correctly
- Frontend doesn’t reflect new settings fields:
  - settings schema not exposed consistently to UI
- Non-deterministic outcomes:
  - capture model parameters, seeds, and configs explicitly

## Next pages

- `/en/sdk/overview` — how the SDK fits into the platform
- `/en/sdk/plugins` — plugin types and responsibilities (SDK-level)
- `/en/sdk/schemas` — the primary models you will interact with
- `/en/sdk/examples` — starter examples you can copy

Spanish version (placeholder):
- `/es/guides/plugins`

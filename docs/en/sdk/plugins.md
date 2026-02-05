---
title: Plugins
description: How plugins work in Fair Platform and which types you can implement.
---

This page is an **English placeholder** for the SDK plugins documentation. It exists to prevent 404s and to provide a stable URL while the full SDK docs are being expanded.

## What is a plugin?

A **plugin** is an extension module that Fair Platform can:

- discover at startup
- validate configuration for (via a settings schema)
- run as part of grading workflows

Plugins are the primary way to add new capabilities without changing Fair Platform core.

## Common plugin types (conceptual)

Depending on your use case, you may want to implement one (or more) of these categories:

- **Transcriber / Interpreter**  
  Converts raw submissions (PDFs, images, notebooks, ZIPs, etc.) into standardized **artifacts** the rest of the system can process.

- **Grader**  
  Evaluates artifacts and produces grades and feedback. This can be rubric-based, LLM-based, hybrid, or agent-driven.

- **Validator**  
  Performs checks and adds warnings/flags (format constraints, compile checks, proof verification, etc.).

- **Storage backend**  
  Changes how artifacts/results/datasets are stored and retrieved.

## Settings (configuration)

A key design point is that plugins should expose **typed settings** so that:

- the backend can validate configs
- the UI can render configuration forms
- experiments stay reproducible (configs can be exported/imported)

Avoid placing secrets in these settings. Use environment variables or secret management for API keys.

## Minimal checklist for a new plugin

When you add a plugin, you generally need to:

1. Choose the plugin type(s) and responsibilities
2. Define plugin metadata (name/id, version, etc.)
3. Define a settings schema (what the user can configure)
4. Implement the runtime behavior (what runs on submissions/artifacts)
5. Ensure it is discoverable by the backend plugin loader
6. Test it end-to-end through the UI/API

## Next pages

- `en/sdk/overview`
- `en/sdk/schemas`
- `en/sdk/examples`

Spanish placeholder:

- `es/sdk/plugins`

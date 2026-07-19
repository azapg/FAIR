---
title: Capabilities
description: Define one versioned function that FAIR can call.
---

A **Capability** is a versioned function exposed by an Extension. FAIR calls Capabilities; it does not need to know which model, agent framework, or library implements them.

Examples: `chat.assignment`, `grade.submission`, `slides.generate`, or `search.library`.

## Capability kinds

| Kind | Use it for |
| --- | --- |
| `agent` | Multi-step AI behavior or chat. |
| `grader` | Feedback or grading proposals. |
| `transformer` | Converting one input into another. |
| `tool` | A callable operation another Capability may use. |
| `integration` | Connecting FAIR to an external system. |

The kind helps people discover the Capability. Every kind uses the same Execution protocol.

## Required contract

Each Capability declares:

- `capabilityId`, `kind`, and `version`;
- `inputSchema` and `outputSchema` using JSON Schema Draft 2020-12;
- optional `configSchema`;
- requested permissions in `requestedScopes` and `declaredEffects`;
- optional `toolCapabilities` it may invoke;
- support flags for streaming, cancellation, resume, and batching.

FAIR freezes the exact Capability version and schemas onto each Execution. Updating an Extension does not change work that already started.

## Choosing support flags

| Flag | Set it when... |
| --- | --- |
| `supportsStreaming` | the Capability emits progressive output. |
| `supportsCancellation` | your code can stop active work. |
| `supportsResume` | it may pause for user input and continue. |
| `supportsBatch` | one call can process multiple items. |

Next: [Installations and grants](/en/extensions/installations) explains how FAIR decides where and when a Capability may run.

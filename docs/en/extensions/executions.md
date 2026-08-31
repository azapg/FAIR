---
title: Executions
description: Understand the command and lifecycle for one Capability run.
---

An **Execution** is one attempt to run a Capability. It records identity, status, inputs, outputs, events, and provenance.

## ExecutionCommand

FAIR sends one `ExecutionCommand` for `start`, `resume`, or `cancel`.

The fields Extension authors use most are:

| Field | Meaning |
| --- | --- |
| `commandId` | One durable delivery record. |
| `idempotencyKey` | One logical command. Use it to prevent duplicate effects. |
| `command` | `start`, `resume`, or `cancel`. |
| `execution` | Execution ID, Capability pin, scope, deadline, and input Artifacts. |
| `authorization` | Short-lived token and allowed scopes. |
| `payload` | Input for this command. |
| `platformUrl` | FAIR API origin to call. |

Webhook and runner delivery use the same command shape.

## Lifecycle

```text
queued -> running -> waiting -> running -> terminal
```

Terminal means `completed`, `failed`, `cancelled`, or `expired`. An HTTP disconnect, stopped process, or closed stream is not success.

If a Capability supports resume, it may request user input and enter `waiting`. FAIR resolves the interaction and sends a `resume` command.

## Rules that prevent duplicate work

- Delivery is at least once. Store and deduplicate `idempotencyKey` before causing effects.
- Retrying the same accepted Event is safe.
- Reusing an idempotency key with different content returns `409`.
- Exactly one terminal result can win.

The canonical command fixture is `specs/fixtures/execution-command.json`. The normative contract is `specs/extension-execution-protocol.md`.

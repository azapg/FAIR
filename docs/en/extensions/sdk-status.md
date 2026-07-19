---
title: SDK status
description: See what works today and what the public SDK still needs.
---

The raw Extension Execution Protocol is implemented. The standalone developer SDKs are not finished.

## Available now

- strict manifests and Capability schemas;
- one `ExecutionCommand` for webhook and runner delivery;
- signed webhook commands;
- outbound runner claim, lease, and acknowledgement;
- execution-scoped tokens;
- idempotent Event ingestion;
- replayable SSE;
- lifecycle, cancellation, and resume primitives;
- version-pinned Artifact reads and managed JSON outputs;
- platform-linked tool calls as child Executions.

The Python code under `fair_platform.extension_sdk` is an internal reference implementation. It is not yet a stable standalone package.

## TODO

- standalone Python SDK;
- standalone TypeScript SDK;
- simple agent and chat helpers;
- managed binary Artifact upload;
- typed cross-language conformance fixtures;
- external multi-worker and restart test harness;
- assignment binding and GradeProposal workflow;
- public installation and grant workflow.

## Source of truth

| Source | Purpose |
| --- | --- |
| `specs/extension-execution-protocol.md` | normative Protocol 1 rules |
| `specs/fixtures/` | language-neutral contract examples |
| `fair_platform.extension_sdk` | internal Python reference |
| repository tests | reproducible conformance evidence |

The reference pages explain the model. The normative spec decides protocol behavior when wording differs.

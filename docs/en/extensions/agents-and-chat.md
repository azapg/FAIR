---
title: Agents and chat
description: Map agent loops and streamed chat onto Capabilities and Events.
---

An AI agent or chat assistant is an `agent` Capability. FAIR does not require a specific model provider or agent framework.

## Basic mapping

| Agent concept | FAIR concept |
| --- | --- |
| agent definition | Capability |
| one conversation turn | Execution |
| streamed response | message Events |
| user approval or question | interaction request and resume command |
| durable output | Artifact |
| FAIR-managed tool call | child Execution |

Keep the private agent loop inside your Extension. Report only the updates, interactions, tool calls, and outputs FAIR needs to authorize or preserve.

For streaming, send bounded `message.delta` chunks. Product clients reconnect to FAIR with `Last-Event-ID`; they do not connect directly to the model provider.

<Warning>
TODO: Build the assignment-first chat UI, conversation helpers, and standalone SDK adapters on top of the implemented Execution and Event protocol.
</Warning>

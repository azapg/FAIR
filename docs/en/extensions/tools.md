---
title: Tools
description: Choose between private tools and FAIR-managed tool Executions.
---

An agent can use two kinds of tools.

| Tool type | Use it when... |
| --- | --- |
| Private tool | the call is internal to your Extension and needs no FAIR record or authorization. |
| Platform-linked tool | FAIR must authorize, run, or preserve the call. |

A platform-linked tool is another Capability. Calling it creates a child Execution.

## Declare tools

The parent Capability must:

- request `tools:invoke`;
- list allowed semantic Capability IDs in `toolCapabilities`.

## Call tools

```text
POST /api/v1/executions/{parentExecutionId}/tools
GET  /api/v1/executions/{parentExecutionId}/tools/{toolExecutionId}
```

Send a caller-generated `idempotencyKey`. FAIR validates the allowlist, input schema, Installation, and Grants before dispatch. It validates successful output against the tool's frozen output schema.

Use private tools by default. Use platform-linked tools when the call needs policy, provenance, or independent observation.

<Warning>
TODO: Add ergonomic tool adapters and typed result helpers to the standalone SDKs.
</Warning>

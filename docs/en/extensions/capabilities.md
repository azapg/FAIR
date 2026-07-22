---
title: Capabilities and Surfaces
description: Declare what your Extension can do and where it plugs into FAIR.
---

A **Capability** is one versioned function an Extension exposes. Every
Capability picks a **Surface**.

## Surfaces

A Surface answers the only two questions FAIR needs: where does this appear in
the product, and whose schema governs its input and output?

| Surface | Placement | Schema owner | Lifecycle |
| --- | --- | --- | --- |
| `chat.agent` | model selector, chat threads | FAIR | streaming, cancellable |
| `function` | a button wherever its contract is placed | the contract | request/response |
| `flow.step` | selectable as a Flow node | you | request/response |

Adding a Surface later does not change the Execution protocol: every Surface
compiles to the same `ExecutionCommand` and the same durable event log.

## Contracts

The `function` Surface implements a FAIR-owned **contract**, such as
`fair.rubric.generate@1`. The contract defines:

- the input and output schema;
- the UI placements where FAIR renders a button for it.

That indirection is the point. A new feature ("generate a course description",
"define this term") is a new contract file plus a placement — not a protocol
change, not an SDK release. Extensions that implement a contract light up
wherever it is placed, and a different Extension can take the contract over
without the UI changing.

Callers invoke a contract, never an extension id:

```text
POST /api/v1/functions/invoke
{"contract": "fair.rubric.generate@1", "input": {...}}
```

## Declared fields

| Field | Meaning |
| --- | --- |
| `capabilityId` | stable id within the Extension |
| `surface` | one of the three above |
| `version` | capability version; FAIR pins this onto every run |
| `contract` | required for `function`, rejected otherwise |
| `displayName` / `description` | what people see |
| `declaredEffects` | consequential actions needing a Grant |
| `supportsStreaming` / `supportsCancellation` / `supportsResume` | runtime features |

## What you do not declare

**Scopes.** The Surface implies them. A `chat.agent` gets
`executions:events`, `artifacts:read` and `artifacts:write`; a `function` gets
`executions:events`. You declare consequential *effects*, not the plumbing
needed to report your own work.

**Schemas.** For `chat.agent` and `function` the Surface or contract owns the
schema. For `flow.step` the SDK derives it from your declared types. FAIR still
freezes a concrete schema onto every capability version — you just do not write
it by hand.

You may still supply an explicit `inputSchema` / `outputSchema` when you want a
stricter contract than the default. FAIR validates it at registration, so an
invalid schema fails when you start the Extension rather than on a user's first
message.

## Versioning

FAIR freezes the exact capability version and its schemas onto each Execution.
Publishing a new version adds a CapabilityDefinition; it never rewrites the one
that in-flight work and published Flow versions already pin.

Next: [Installations and grants](/en/extensions/installations).

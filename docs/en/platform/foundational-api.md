---
title: The foundational API
description: Build Extensions and reproducible Flows on FAIR's single execution model.
---

FAIR 1.0 has one boundary for custom behavior: an installed **Extension capability** is invoked through an **Execution**. AI, agents, graders, renderers, and connectors are implementations behind that boundary, not special platform services.

## Resource map

| Resource | Purpose | Canonical path |
|---|---|---|
| ExtensionInstallation | trusted deployment and dispatch target | `/api/v1/extensions/installations` |
| CapabilityDefinition | versioned callable contract from a manifest | `/api/v1/extensions/capabilities` |
| ExtensionGrant | contextual allow or deny decision | `/api/v1/extensions/grants` |
| Execution | one durable attempt to do work | `/api/v1/executions` |
| ExecutionEvent | ordered, idempotent fact emitted during work | `/api/v1/executions/{id}/events` |
| ArtifactVersion | immutable output or evidence with provenance | `/api/v1/artifact-versions` |
| FlowVersion | immutable ordered procedure with capability pins | `/api/v1/flows/{id}/versions` |

`Workflow`, `WorkflowRun`, public `Job`, and `Plugin` are not part of this model. Their endpoints and tables were removed rather than aliased because their semantics were different.

## Three authorization layers

1. **User authorization.** User requests carry a FAIR bearer token. Role capabilities and resource ownership control who may create, read, update, or execute a Flow and who may see an Execution or Artifact.
2. **Installation and grant authorization.** A capability can execute only through an enabled installation. Contextual grants constrain declared effects by course, assignment, or platform scope.
3. **Extension client authorization.** Extensions authenticate calls back to FAIR with an issued client secret and required scopes such as `executions:events` or `artifacts:write`. Secrets are shown only when issued or rotated.

<Warning>
Outbound dispatch currently uses durable direct HTTP with stable dispatch and idempotency headers. Platform-to-Extension cryptographic request signing is still being hardened; keep dispatch endpoints behind trusted transport and network controls until signed dispatch is available.
</Warning>

## Capability contract

An Extension manifest declares its identity, version, dispatch URL, and one or more capabilities. Every capability declares:

- a stable capability ID, kind, and version;
- input, output, and optional configuration schemas;
- requested scopes and declared effects;
- whether it supports streaming, cancellation, resume, or batching.

FAIR snapshots the manifest into the installation and stores each capability definition separately. A FlowVersion pins the exact definition and installation snapshot so a later Extension upgrade cannot silently change a published experiment.

## Execution lifecycle

```text
intent
  -> authorize user, installation, capability, context, and effects
  -> create Execution and immutable start events
  -> commit a dispatch command in the same database transaction
  -> deliver the command to the installed Extension
  -> accept scoped, idempotent Execution Events
  -> project status, messages, interactions, Artifacts, and proposals
  -> complete, fail, cancel, or expire
```

Delivery is at-least-once. The `Idempotency-Key` and `X-FAIR-Dispatch-Id` headers are stable across retries, so an Extension must treat a repeated command as the same request. FAIR also deduplicates inbound events by producer identity.

Public clients observe Executions and events. Dispatch leases, attempts, and dead-letter state remain internal implementation details.

## One task versus a Flow

Use one Execution when a caller needs one capability invocation. Use a FlowVersion when order and exact inputs must be repeatable.

Starting a published FlowVersion creates a root Execution and the first step Execution. The ordered runtime then:

- resolves each pinned capability and contextual grant;
- creates a linked child Execution for every attempt;
- passes the previous step output into the next node;
- applies node timeout, retry, and `fail` or `continue` policy;
- propagates cancellation and expiry;
- records the terminal root summary and full lineage.

The database is the restart boundary: advancement is derived from durable Executions and events, not process memory.

## Artifacts and consequential outcomes

An Artifact is a logical resource; an ArtifactVersion is immutable after finalization. Parts can contain inline structured data or storage references, and links connect versions to Executions, submissions, assignments, courses, messages, and other provenance targets.

An Extension may create an Artifact only for the Execution it is servicing. FAIR records the producing installation and Execution. Completing an Execution does not silently publish a grade: Extensions may create proposals, while domain decisions remain explicit and attributable.

## Contract source

The API Reference tab is generated from the running FastAPI OpenAPI document. Treat it as the field-level source of truth; use this page for lifecycle and boundary semantics.

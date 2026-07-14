---
title: Core and Extensions
description: Understand FAIR's thin platform core and the boundary for custom behavior.
---

FAIR is designed to remain useful with no Extensions installed. In that state it provides the durable education layer: people, courses, assignments, submissions, rubrics, authorization, artifacts, and human decisions.

Extensions add behavior. AI graders, personalized teaching assistants, slide generators, transcription, external connectors, and deterministic tools are all Extensions—not services embedded in the FAIR backend.

## The foundational rule

The platform owns **state, policy, and observation**. An Extension owns **behavior**.

| Platform core | Installed Extension |
|---|---|
| authenticates users and installations | implements one or more capabilities |
| authorizes access to courses and resources | chooses models, frameworks, prompts, and providers |
| creates and records Executions | receives a scoped execution command |
| accepts ordered Execution Events | performs custom or AI work |
| stores Artifacts and provenance | emits progress, outputs, and proposals |
| records human review and final decisions | never silently publishes a consequential decision |

FAIR does not have a global AI service. Provider credentials and model configuration belong to an Extension installation or to the Extension's own deployment environment.

## Canonical lifecycle

```text
User or system intent
  -> Execution
  -> transactional dispatch outbox
  -> installed Extension capability
  -> ordered Execution Events
  -> projections, Artifacts, interactions, and proposals
  -> explicit human or domain decision when required
```

Clients observe the Execution. Queue and delivery records are internal implementation details.

## Foundational resources

- **ExtensionInstallation** is a trusted installed instance of an Extension.
- **CapabilityDefinition** is a versioned callable behavior declared by that installation.
- **ExtensionGrant** authorizes a capability in a specific context and scope.
- **Execution** is one attempt to invoke a capability or a published FlowVersion.
- **ExecutionEvent** is an accepted, immutable fact ordered within one Execution.
- **Artifact** and its immutable versions preserve outputs and provenance.
- **FlowVersion** pins an ordered, reproducible composition of capabilities and configuration.

## Canonical API surface

The new foundation lives under `/api/v1`:

| Resource | Base path |
|---|---|
| Extension installations, capabilities, and grants | `/api/v1/extensions` |
| Executions, events, streams, and interactions | `/api/v1/executions` |
| Flows and immutable FlowVersions | `/api/v1/flows` |
| Artifacts, versions, parts, and finalization | `/api/v1/artifacts` |

The `Workflow`, `WorkflowRun`, public `Job`, `Plugin`, and unversioned Artifact endpoints have been removed. There are no compatibility aliases: integrations must use the `/api/v1` resources above.

<Warning>
Extension event ingestion requires scoped client credentials, and every execution checks the selected installation and contextual grants. Outbound commands are durable, idempotent, and retried, but platform-to-Extension request signing remains a FAIR 1.0 hardening item. Deploy Extension dispatch endpoints on a trusted network until signed dispatch is available.
</Warning>

## Why Flows remain first-class

An Execution is enough for one task given to one capability. A Flow adds a pinned, inspectable procedure: exact capability versions, configuration, order, inputs, and linked step Executions. This makes deterministic and AI-assisted experiments comparable and reproducible without creating a second execution system.

Read [The foundational API](/en/platform/foundational-api) for the resource contracts, authorization layers, and execution lifecycle.

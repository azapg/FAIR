---
title: Flows and Executions
description: Build reproducible procedures from installed Extension capabilities.
---

A **Flow** is the logical identity of a reusable procedure. A **FlowVersion** is an immutable executable snapshot of its ordered nodes, pinned capability versions, and configuration.

Starting a published FlowVersion creates one root **Execution**. Each node runs as a linked step Execution on the same event, Artifact, authorization, and review substrate used by agents and one-off capabilities.

## Why both concepts exist

- Use an **Execution** for one attempt to perform one capability or published FlowVersion.
- Use a **FlowVersion** when the exact procedure must be inspected, repeated, compared, or cited in research.
- A Flow does not require an LLM or an agent.
- An agent may invoke a published Flow, but it does not replace the pinned Flow definition.

## Reproducibility record

A Flow Execution preserves:

- the immutable FlowVersion identifier and definition hash;
- exact capability and configuration pins;
- ordered root and step Execution lineage;
- accepted ordered events and terminal state;
- input and output Artifact provenance.

## Current API

Flow resources live under `/api/v1/flows`. The API supports creating and archiving Flows, creating immutable versions, publishing or archiving a version, and starting a Flow Execution.

The runtime executes nodes in definition order. Each step is a child Execution with a pinned capability and installation. A completed step feeds its output to the next node. Node policy controls timeout, maximum attempts, and whether failure stops or continues the Flow. Cancellation and expiry propagate to active steps, and the root Execution records the terminal summary.

The removed `/api/workflows` and `/api/workflow-runs` resources have no compatibility aliases.

See [Core and Extensions](/en/platform/extension-architecture) for the shared lifecycle and API boundary.

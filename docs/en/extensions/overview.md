---
title: Extensions overview
description: Start here to understand Extensions, Capabilities, and Executions.
---

When you want to add behavior to FAIR, you create an **Extension**. An Extension exposes one or more **Capabilities**: versioned functions FAIR can call.

Examples of Capabilities include an assignment agent, chat assistant, grader, file transformer, tool, or external integration.

## Mental model

| Concept | Meaning |
| --- | --- |
| Extension | The package or service that contains your code. |
| Manifest | The JSON document that describes the Extension. |
| Capability | One versioned function exposed by the Extension. |
| Installation | One trusted copy of an Extension connected to FAIR. |
| Execution | One attempt to run a Capability. |
| Event | A durable update from an Execution. |
| Artifact | A typed input or output, such as JSON or a file. |

FAIR owns authorization, durable state, streaming to clients, and final decisions. Your Extension owns its models, prompts, tools, provider credentials, and custom code.

## What happens when FAIR calls a Capability?

```text
Assignment or Flow
  -> Capability
  -> ExecutionCommand
  -> your Extension
  -> Events and Artifacts
  -> completed, failed, cancelled, or expired
```

The same model works for agents, graders, tools, and Flow steps. Your code can receive commands through an HTTPS webhook or claim them from a local runner.

## Find the right page

| If you need to... | Read... |
| --- | --- |
| describe your Extension | [Extensions and manifests](/en/extensions/manifests) |
| define something FAIR can call | [Capabilities](/en/extensions/capabilities) |
| understand one run | [Executions](/en/extensions/executions) |
| run code on a laptop or server | [Delivery](/en/extensions/delivery) |
| stream agent or chat output | [Events and streaming](/en/extensions/events) |
| read or produce files and JSON | [Artifacts](/en/extensions/artifacts) |
| let an agent call FAIR-managed tools | [Tools](/en/extensions/tools) |
| understand tokens and permissions | [Security](/en/extensions/security) |
| check what is implemented | [SDK status](/en/extensions/sdk-status) |

---
title: Build an Extension
description: Ship a streaming chat agent on FAIR in about five minutes.
---

An **Extension** is a process you run that FAIR can call. This page takes you
from nothing to a working agent in the model selector.

You need [Bun](https://bun.com/get) and a running FAIR instance.

## 1. Get a credential

On the machine running FAIR:

```bash
fair ext bootstrap org.example.tutor
```

It prints a secret once (FAIR only stores its hash) and the two environment
variables your Extension needs. The credential can do exactly two things:
claim this Extension's own work, and publish its own manifest. It can never
read educational data.

## 2. Write the Extension

```bash
mkdir tutor && cd tutor
bun init -y
bun add @fair/sdk ai @ai-sdk/openai
```

```ts
// src/index.ts
import { createExtension, agentCapability } from '@fair/sdk';
import { ToolLoopAgent } from 'ai';
import { openai } from '@ai-sdk/openai';

const agent = new ToolLoopAgent({
  model: openai('gpt-5'),
  instructions: 'Guide the student with questions. Never give the answer.',
});

await createExtension({
  id: 'org.example.tutor',
  name: 'Socratic Tutor',
  version: '1.0.0',
  capabilities: [
    agentCapability({ id: 'tutor', name: 'Socratic Tutor', agent }),
  ],
}).start();
```

That is the whole integration. You build the agent however you like and hand
the object over; FAIR calls its own `stream()` and mirrors the text, tool calls
and errors it already emits into the durable Execution log. You do not modify
your agent, and you never write protocol code.

## 3. Run it

```bash
FAIR_PLATFORM_URL=http://127.0.0.1:8000 \
FAIR_EXTENSION_SECRET=<secret> \
bun run src/index.ts
```

```text
[fair] org.example.tutor v1.0.0 ready (1 capabilities, runner alam:33396)
[fair]   - chat.agent: tutor
```

Your agent is now in FAIR's model selector. On boot the SDK derives the
manifest from your code and publishes it, so there is no JSON Schema to write
and no manifest to paste.

Delivery is **runner mode**: the process makes outbound connections only. No
inbound port, no tunnel, no webhook signatures — the same code runs on a laptop
behind NAT and on a server.

## The three Surfaces

A **Surface** is where a capability plugs into FAIR and whose schema governs
its input and output.

| Surface | Appears as | Shape |
| --- | --- | --- |
| `chat.agent` | an option in the model selector | streaming conversation |
| `function` | a button wherever its contract is placed | typed request/response |
| `flow.step` | a node you can pin in a Flow | deterministic input → output |

### chat.agent

Either hand over an agent, or write the loop yourself:

```ts
agentCapability({
  id: 'echo',
  async *run(turn, ctx) {
    yield `You said: ${turn.text}`;      // chunking is the SDK's problem
  },
})
```

Yielded strings are buffered into bounded durable chunks (100ms or 2KB). You
never construct a `message.delta`, and one model token is never one HTTP
request.

### function

Functions implement a **contract** that FAIR owns:

```ts
functionCapability({
  contract: 'fair.rubric.generate@1',
  async run(input, ctx) {
    return { title: '...', totalPoints: 100, criteria: [...] };
  },
})
```

The contract — not your Extension — defines the input/output schema and the
places a button appears. Implementing it is all it takes to light those up.

Callers invoke the contract, never your extension id:

```text
POST /api/v1/functions/invoke
{"contract": "fair.rubric.generate@1", "input": {...}}
```

### flow.step

```ts
flowStep({
  id: 'grade.essay',
  async run(input, ctx) {
    return { score: 87, feedback: '...' };
  },
})
```

Flow steps are plain functions on purpose. Publishing a Flow freezes the exact
capability version of every node, so re-running it next month runs the same
pipeline — which is what makes comparing two Flows a measurement.

## What `ctx` gives you

```ts
ctx.signal                  // aborted on cancellation or deadline
ctx.scope                   // authorized course / assignment / submission
ctx.artifacts.list()        // version-pinned inputs
ctx.artifacts.read(id)
ctx.artifacts.create({ title, kindUri, inlineJson })
ctx.log(message, data)
```

## What the SDK handles for you

You do not write any of this, but it is what you are getting:

- **at-least-once delivery.** Producer event ids derive from the command's
  idempotency key, so a redelivered command replays onto the same events
  instead of duplicating them.
- **exactly one terminal outcome.** Throw, return, or get cancelled — the SDK
  reports one, and drops later attempts so an error handler cannot race a
  success that already landed.
- **token refresh** before the execution token expires.
- **bounded streaming chunks** instead of one request per token.
- **cancellation and deadlines** wired to `ctx.signal`.

## Next

- [Executions](/en/extensions/executions) — the lifecycle of one run
- [Events and streaming](/en/extensions/events) — the durable log behind it
- [Security](/en/extensions/security) — credentials, scopes, and grants

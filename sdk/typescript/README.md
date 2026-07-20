# @fair/sdk

Build a FAIR Extension. You write your agent; the SDK handles the protocol.

```bash
bun add @fair/sdk
```

## The whole integration

```ts
import { createExtension, agentCapability } from '@fair/sdk';
import { ToolLoopAgent } from 'ai';
import { openai } from '@ai-sdk/openai';

const agent = new ToolLoopAgent({
  model: openai('gpt-5'),
  instructions: 'Guide the student. Never give the answer.',
});

await createExtension({
  id: 'org.example.tutor',
  name: 'Socratic Tutor',
  version: '1.0.0',
  capabilities: [agentCapability({ id: 'tutor', agent })],
}).start();
```

Your agent is not modified, wrapped, or monkey-patched. The SDK calls its own
`stream()` and reads the `fullStream` it already produces, translating text,
tool calls, reasoning and errors into FAIR's durable event log. Consuming that
one ordered stream is also what keeps those in the order the agent produced
them.

Any object with `stream({ messages }) -> { fullStream }` works — that is
structurally AI SDK's `Agent` interface, so `Agent` and `ToolLoopAgent` both
fit. An `agent` without a `stream()` method throws at registration with a
message naming the fix, rather than degrading at runtime.

## The three surfaces

```ts
agentCapability({ id, agent })                    // or { id, run }
functionCapability({ contract, run })
flowStep({ id, run, inputSchema?, outputSchema? })
```

See [Build an Extension](https://docs.fairgradeproject.org/en/extensions/quickstart).

## Configuration

| Variable | Meaning |
| --- | --- |
| `FAIR_PLATFORM_URL` | your FAIR instance |
| `FAIR_EXTENSION_SECRET` | from `fair ext bootstrap <extension-id>` |

Delivery is runner mode: outbound connections only, so no inbound port, tunnel,
or webhook signature handling in development.

## What you are not writing

- producer event identity and dedupe under at-least-once delivery
- exactly-one-terminal-outcome, including on throw and on cancel
- execution token refresh
- bounded streaming chunks (100ms / 2KB) instead of one request per token
- manifest JSON and JSON Schema — both derived from your code and synced on boot

## Development

```bash
bun install      # from the repo root; this is a workspace
bun run build:sdk
bun run typecheck
```

`extensions/core/` is FAIR's own extension built on this SDK, and doubles as
the worked example.

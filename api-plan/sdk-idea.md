You would **not mutate or inject into the existing `ToolLoopAgent` instance**. Instead, `createAgentExtension()` should return an adapter that calls the agent’s existing `generate()` and `stream()` methods while adding your callbacks and stream transformation.

That distinction matters:

```ts
const rawAgent = new ToolLoopAgent({ ... });

const agent = createAgentExtension({
  id: 'essay-grader',
  framework: 'ai-sdk',
  agent: rawAgent,
});
```

Your returned `agent` is the instrumented version developers expose to your LMS.

Vercel’s `ToolLoopAgent.generate()` and `.stream()` accept per-call callbacks for agent start, step start, tool start, tool completion/error, step completion, and final completion. The streaming method also accepts `experimental_transform`, which lets you inspect streaming chunks while passing them through unchanged. ([AI SDK][1])

## Recommended public API

```ts
const rawAgent = new ToolLoopAgent({
  model: 'anthropic/claude-sonnet-4.5',
  instructions: 'Grade essays according to the rubric.',
  tools: {
    getSubmission,
    updateGrade,
  },
});

export default createAgentExtension({
  id: 'essay-grader',
  framework: 'ai-sdk',
  agent: rawAgent,
});
```

Then developers should call your returned adapter, rather than the raw agent:

```ts
const result = extension.stream({
  messages,
  context: {
    courseId,
    studentId,
    submissionId,
  },
});
```

## Concrete implementation

Here is the basic shape I would use:

```ts
import type { ToolLoopAgent } from 'ai';

type ExtensionEvent =
  | {
      type: 'agent.started';
      runId: string;
      extensionId: string;
    }
  | {
      type: 'step.started';
      runId: string;
      stepNumber: number;
    }
  | {
      type: 'tool.started';
      runId: string;
      toolCallId: string;
      toolName: string;
      input: unknown;
    }
  | {
      type: 'tool.completed';
      runId: string;
      toolCallId: string;
      toolName: string;
      output: unknown;
      durationMs: number;
    }
  | {
      type: 'tool.failed';
      runId: string;
      toolCallId: string;
      toolName: string;
      error: unknown;
      durationMs: number;
    }
  | {
      type: 'text.delta';
      runId: string;
      delta: string;
    }
  | {
      type: 'reasoning.delta';
      runId: string;
      delta: string;
    }
  | {
      type: 'agent.completed';
      runId: string;
      text?: string;
      usage?: unknown;
    }
  | {
      type: 'agent.failed';
      runId: string;
      error: unknown;
    };

interface EventReporter {
  emit(event: ExtensionEvent): void | Promise<void>;
}

interface CreateAgentExtensionOptions<TAgent extends ToolLoopAgent<any, any, any>> {
  id: string;
  framework: 'ai-sdk';
  agent: TAgent;
  reporter: EventReporter;
}

export function createAgentExtension<
  TAgent extends ToolLoopAgent<any, any, any>,
>({
  id,
  agent,
  reporter,
}: CreateAgentExtensionOptions<TAgent>) {
  return {
    id,
    framework: 'ai-sdk' as const,
    rawAgent: agent,

    async generate(
      input: Parameters<TAgent['generate']>[0],
    ): Promise<Awaited<ReturnType<TAgent['generate']>>> {
      const runId = crypto.randomUUID();

      try {
        return await agent.generate({
          ...input,

          experimental_context: {
            ...(isObject(input.experimental_context)
              ? input.experimental_context
              : {}),
            extensionId: id,
            runId,
          },

          experimental_onStart: async () => {
            await reporter.emit({
              type: 'agent.started',
              extensionId: id,
              runId,
            });

            await input.experimental_onStart?.(...arguments);
          },

          experimental_onStepStart: async event => {
            await reporter.emit({
              type: 'step.started',
              runId,
              stepNumber: event.stepNumber,
            });

            await input.experimental_onStepStart?.(event);
          },

          experimental_onToolCallStart: async event => {
            await reporter.emit({
              type: 'tool.started',
              runId,
              toolCallId: event.toolCall.toolCallId,
              toolName: event.toolCall.toolName,
              input: event.toolCall.input,
            });

            await input.experimental_onToolCallStart?.(event);
          },

          experimental_onToolCallFinish: async event => {
            if (event.success) {
              await reporter.emit({
                type: 'tool.completed',
                runId,
                toolCallId: event.toolCall.toolCallId,
                toolName: event.toolCall.toolName,
                output: event.output,
                durationMs: event.durationMs,
              });
            } else {
              await reporter.emit({
                type: 'tool.failed',
                runId,
                toolCallId: event.toolCall.toolCallId,
                toolName: event.toolCall.toolName,
                error: serializeError(event.error),
                durationMs: event.durationMs,
              });
            }

            await input.experimental_onToolCallFinish?.(event);
          },

          onStepFinish: async event => {
            await input.onStepFinish?.(event);
          },

          onFinish: async event => {
            await reporter.emit({
              type: 'agent.completed',
              runId,
              usage: event.totalUsage,
            });

            await input.onFinish?.(event);
          },
        });
      } catch (error) {
        await reporter.emit({
          type: 'agent.failed',
          runId,
          error: serializeError(error),
        });

        throw error;
      }
    },

    stream(input: Parameters<TAgent['stream']>[0]) {
      const runId = crypto.randomUUID();

      return agent.stream({
        ...input,

        experimental_context: {
          ...(isObject(input.experimental_context)
            ? input.experimental_context
            : {}),
          extensionId: id,
          runId,
        },

        experimental_onStart: async event => {
          await reporter.emit({
            type: 'agent.started',
            extensionId: id,
            runId,
          });

          await input.experimental_onStart?.(event);
        },

        experimental_onStepStart: async event => {
          await reporter.emit({
            type: 'step.started',
            runId,
            stepNumber: event.stepNumber,
          });

          await input.experimental_onStepStart?.(event);
        },

        experimental_onToolCallStart: async event => {
          await reporter.emit({
            type: 'tool.started',
            runId,
            toolCallId: event.toolCall.toolCallId,
            toolName: event.toolCall.toolName,
            input: event.toolCall.input,
          });

          await input.experimental_onToolCallStart?.(event);
        },

        experimental_onToolCallFinish: async event => {
          if (event.success) {
            await reporter.emit({
              type: 'tool.completed',
              runId,
              toolCallId: event.toolCall.toolCallId,
              toolName: event.toolCall.toolName,
              output: event.output,
              durationMs: event.durationMs,
            });
          } else {
            await reporter.emit({
              type: 'tool.failed',
              runId,
              toolCallId: event.toolCall.toolCallId,
              toolName: event.toolCall.toolName,
              error: serializeError(event.error),
              durationMs: event.durationMs,
            });
          }

          await input.experimental_onToolCallFinish?.(event);
        },

        experimental_transform: [
          createExtensionStreamObserver({
            runId,
            reporter,
          }),
          ...normalizeTransforms(input.experimental_transform),
        ],

        onStepFinish: async event => {
          await input.onStepFinish?.(event);
        },

        onFinish: async event => {
          await reporter.emit({
            type: 'agent.completed',
            runId,
            usage: event.totalUsage,
          });

          await input.onFinish?.(event);
        },
      });
    },
  };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function normalizeTransforms<T>(value: T | T[] | undefined): T[] {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function serializeError(error: unknown) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
    };
  }

  return {
    message: String(error),
  };
}
```

The typing may need slight adjustment against the precise generic declarations in the installed AI SDK release, but the integration architecture is the important part.

## Observing text and reasoning

The lifecycle callbacks handle tools and agent steps, but they do not deliver every streaming text token.

For that, add a transparent stream transform:

```ts
import type {
  StreamTextTransform,
  ToolSet,
} from 'ai';

function createExtensionStreamObserver<TOOLS extends ToolSet>({
  runId,
  reporter,
}: {
  runId: string;
  reporter: EventReporter;
}): StreamTextTransform<TOOLS> {
  return () =>
    new TransformStream({
      async transform(part, controller) {
        try {
          switch (part.type) {
            case 'text-delta':
              await reporter.emit({
                type: 'text.delta',
                runId,
                delta: part.text,
              });
              break;

            case 'reasoning-delta':
              await reporter.emit({
                type: 'reasoning.delta',
                runId,
                delta: part.text,
              });
              break;
          }
        } finally {
          // Critical: preserve the original AI SDK stream.
          controller.enqueue(part);
        }
      },
    });
}
```

The exact property on a delta may be named according to the stream-part type in the installed release, so you should compile this against AI SDK 6 and use its exported discriminated unions.

The important behavior is:

```ts
observe(part);
controller.enqueue(part);
```

Your LMS sees the event, while the application still receives the original stream.

## You may not need separate text listeners

AI SDK’s streaming result already carries structured parts for:

* text
* reasoning, when exposed by the model/provider
* tool-input start and deltas
* completed tool calls
* tool results
* errors
* step boundaries
* finish events

So another viable architecture is to make the AI SDK stream itself your source of truth and convert those parts into your protocol:

```text
AI SDK full stream
        ↓
AI SDK adapter
        ↓
Extensions Protocol
        ↓
SSE / WebSocket
        ↓
LMS UI
```

This may be better than emitting text separately through `reporter.emit()`, because it preserves ordering between reasoning, messages, and tools.

For example:

```ts
async function* toExtensionEvents(fullStream: AsyncIterable<any>, runId: string) {
  for await (const part of fullStream) {
    switch (part.type) {
      case 'text-delta':
        yield {
          type: 'message.delta',
          runId,
          delta: part.text,
        };
        break;

      case 'reasoning-delta':
        yield {
          type: 'reasoning.delta',
          runId,
          delta: part.text,
        };
        break;

      case 'tool-call':
        yield {
          type: 'tool.requested',
          runId,
          toolName: part.toolName,
          toolCallId: part.toolCallId,
          input: part.input,
        };
        break;

      case 'tool-result':
        yield {
          type: 'tool.result',
          runId,
          toolName: part.toolName,
          toolCallId: part.toolCallId,
          output: part.output,
        };
        break;

      case 'error':
        yield {
          type: 'agent.error',
          runId,
          error: serializeError(part.error),
        };
        break;
    }
  }
}
```

However, do not blindly consume `fullStream` in the background and also return it to the developer. Web streams are generally single-consumer unless explicitly split. A pass-through transform is safer.

## What the wrapper can observe

From the existing agent, without changing its tools:

| Information           | Mechanism                                             |
| --------------------- | ----------------------------------------------------- |
| Agent started         | `experimental_onStart`                                |
| LLM step started      | `experimental_onStepStart`                            |
| Tool about to execute | `experimental_onToolCallStart`                        |
| Tool succeeded        | `experimental_onToolCallFinish` with `success: true`  |
| Tool failed           | `experimental_onToolCallFinish` with `success: false` |
| Tool duration         | `durationMs` on tool-finish event                     |
| Step completed        | `onStepFinish`                                        |
| Agent completed       | `onFinish`                                            |
| Text streaming        | `experimental_transform` / full stream                |
| Reasoning streaming   | reasoning stream parts, when provider exposes them    |
| Top-level exception   | wrapper `try/catch`, or stream error parts            |
| Cancellation          | `AbortSignal` plus emitted cancellation handling      |

Vercel documents that the tool-start callback runs immediately before the tool’s `execute` function, while tool-finish runs after execution or error and gives you `success`, `output` or `error`, and `durationMs`. ([AI SDK][1])

## Preserve callbacks supplied by developers

Your wrapper should compose callbacks rather than replace them:

```ts
experimental_onToolCallStart: async event => {
  await yourObserver.onToolStart(event);
  await developerCallback?.(event);
}
```

That means the extension SDK remains non-invasive. A developer can still use their own callbacks.

I would define the order explicitly:

```text
1. LMS callback
2. Extension developer callback
3. Underlying execution continues
```

For completion callbacks:

```text
1. Underlying execution finishes
2. LMS callback
3. Extension developer callback
```

You should also decide whether an error in your reporting layer can break the agent. Usually it should not:

```ts
async function safelyReport(event: ExtensionEvent) {
  try {
    await reporter.emit(event);
  } catch (reportingError) {
    console.error('Extension event reporting failed', reportingError);
  }
}
```

For an LMS UI, I would make reporting failures non-fatal except for events involving required human approval or security policy.

## The limitation of accepting an already-created agent

This syntax:

```ts
createAgentExtension({
  id: 'essay-grader',
  framework: 'ai-sdk',
  agent,
});
```

lets you add **per-run lifecycle callbacks** because `agent.generate()` and `agent.stream()` accept them. It does not give you access to reconstruct or replace the model stored inside an already-created agent.

Therefore, you cannot reliably do this after registration:

```ts
agent.model = wrapLanguageModel({
  model: agent.model,
  middleware: extensionsMiddleware,
});
```

The documented `ToolLoopAgent` API accepts the model in its constructor, but it does not document a public model getter/setter for replacing it afterward. ([AI SDK][1])

That means there are two integration tiers.

### Tier 1: Existing-agent adapter

```ts
createAgentExtension({
  agent: existingAgent,
});
```

Use per-call agent callbacks and stream transforms.

This is enough for your principal needs:

* tool executions
* errors
* steps
* messages
* exposed reasoning
* final results

### Tier 2: Factory-based integration

For complete model-level middleware access, accept a factory:

```ts
createAgentExtension({
  id: 'essay-grader',
  framework: 'ai-sdk',

  createAgent({ wrapModel }) {
    return new ToolLoopAgent({
      model: wrapModel(openai('gpt-5')),
      tools,
      instructions,
    });
  },
});
```

Your SDK then controls model wrapping before the agent is created:

```ts
const extension = createAgentExtension({
  id: 'essay-grader',

  createAgent({ wrapModel }) {
    return new ToolLoopAgent({
      model: wrapModel(openai('gpt-5')),
      tools: {
        getSubmission,
        updateGrade,
      },
    });
  },
});
```

Internally:

```ts
import { wrapLanguageModel } from 'ai';

function buildExtensionModel(model: LanguageModel, reporter: EventReporter) {
  return wrapLanguageModel({
    model,
    middleware: createExtensionLanguageModelMiddleware(reporter),
  });
}
```

Vercel officially documents `wrapLanguageModel()` as returning another language model that can be used wherever the original model would be used. Middleware can intercept non-streaming generation through `wrapGenerate`, streaming through `wrapStream`, and request parameters through `transformParams`. ([AI SDK][2])

## My recommended API

Support both forms:

```ts
// Lowest-friction: observe an existing agent.
createAgentExtension({
  id: 'essay-grader',
  framework: 'ai-sdk',
  agent,
});
```

```ts
// Full integration: your SDK can install model middleware too.
createAgentExtension({
  id: 'essay-grader',
  framework: 'ai-sdk',

  createAgent(runtime) {
    return new ToolLoopAgent({
      model: runtime.wrapModel(openai('gpt-5')),
      tools,
    });
  },
});
```

The existing-agent version should be the default. The factory version can be the advanced path for:

* model request interception
* token-level provider behavior
* prompt policy enforcement
* model substitution
* caching
* guardrails
* provider-specific metadata
* model retry visibility

## Official documentation

Here are the relevant direct links you requested:

* ToolLoopAgent reference, including per-call lifecycle callbacks:
  [https://ai-sdk.dev/docs/reference/ai-sdk-core/tool-loop-agent](https://ai-sdk.dev/docs/reference/ai-sdk-core/tool-loop-agent)

* Language-model middleware and `wrapLanguageModel`:
  [https://ai-sdk.dev/docs/ai-sdk-core/middleware](https://ai-sdk.dev/docs/ai-sdk-core/middleware)

* Tool calling and tool execution:
  [https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling](https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling)

* Telemetry integration:
  [https://ai-sdk.dev/docs/ai-sdk-core/telemetry](https://ai-sdk.dev/docs/ai-sdk-core/telemetry)

* Streaming custom data to an AI SDK UI:
  [https://ai-sdk.dev/docs/ai-sdk-ui/streaming-data](https://ai-sdk.dev/docs/ai-sdk-ui/streaming-data)

* Stream protocol documentation:
  [https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol)

* AI SDK UI tool rendering:
  [https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage](https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage)

One additional design recommendation: make your adapter’s output a canonical `ExtensionRunEvent` stream, and provide a ready-made server handler that turns it into SSE. That would let extension developers register the agent once while your LMS receives an ordered, framework-independent execution timeline.

[1]: https://ai-sdk.dev/docs/reference/ai-sdk-core/tool-loop-agent "AI SDK Core: ToolLoopAgent"
[2]: https://ai-sdk.dev/docs/ai-sdk-core/middleware "AI SDK Core: Language Model Middleware"

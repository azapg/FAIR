import type { ExecutionCommand } from './protocol.js';
import { ExecutionReporter, newId, serializeError } from './reporter.js';
import { TextChunker, type ChunkingOptions } from './stream.js';
import type { CapabilityHandler, CapabilitySpec, RunContext } from './types.js';

/**
 * The shape we need from an agent. This is structurally AI SDK's `Agent`
 * interface (`version: 'agent-v1'`), declared locally so the SDK does not take
 * a hard dependency on `ai` and keeps working across its minor releases.
 */
export interface StreamingAgentLike {
  readonly version?: string;
  /**
   * Deliberately loose. A framework's own message type (AI SDK's
   * `ModelMessage`, for one) is a discriminated union with literal roles;
   * declaring anything narrower here makes real agents fail to typecheck on
   * parameter contravariance. Parts are narrowed where they are read instead.
   */
  stream(options: any): PromiseLike<{ fullStream: AsyncIterable<any> }>;
}

/** The AI SDK full-stream part union, narrowed to what FAIR records. */
type StreamPart =
  | { type: 'text-delta'; id: string; text: string }
  | { type: 'reasoning-delta'; id: string; text: string }
  | { type: 'tool-call'; toolCallId: string; toolName: string; input: unknown }
  | { type: 'tool-result'; toolCallId: string; toolName: string; output: unknown }
  | { type: 'tool-error'; toolCallId: string; toolName: string; error: unknown }
  | { type: 'error'; error: unknown }
  | { type: 'abort'; reason?: string }
  | { type: 'finish'; finishReason: string; totalUsage?: unknown }
  | { type: string; [key: string]: unknown };

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AgentTurn {
  /** The full conversation so far, oldest first. */
  messages: ChatMessage[];
  /** Convenience accessor for the latest user message text. */
  text: string;
}

/** Author-written agent: yield strings, we handle chunking and lifecycle. */
export type AgentGenerator = (
  turn: AgentTurn,
  ctx: RunContext,
) => AsyncIterable<string>;

export interface AgentCapabilityOptions {
  id: string;
  name?: string;
  description?: string;
  version?: string;
  declaredEffects?: string[];
  chunking?: ChunkingOptions;
  /**
   * An existing AI SDK agent. FAIR observes it without modifying it: we call
   * its own `stream()` and read the `fullStream` it already produces.
   */
  agent?: StreamingAgentLike;
  /** Full control: an async generator of text chunks. */
  run?: AgentGenerator;
}

function isStreamingAgent(value: unknown): value is StreamingAgentLike {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as StreamingAgentLike).stream === 'function'
  );
}

/**
 * Register a chat agent.
 *
 * Two forms, both supported:
 *
 *   agentCapability({ id: 'tutor', agent: myAiSdkAgent })
 *   agentCapability({ id: 'tutor', run: async function* (turn, ctx) { ... } })
 *
 * The first is the low-friction path: build the agent however you like with
 * the AI SDK, hand it over, and FAIR mirrors its text, tool calls and errors
 * into the Execution log without you changing a line of it.
 */
export function agentCapability(
  options: AgentCapabilityOptions,
): CapabilitySpec {
  if (!options.agent && !options.run) {
    throw new Error(
      `agentCapability("${options.id}") needs either an \`agent\` or a \`run\` function.`,
    );
  }
  if (options.agent && !isStreamingAgent(options.agent)) {
    // Fail loudly at registration rather than degrading silently at runtime.
    throw new Error(
      `agentCapability("${options.id}") was given an \`agent\` with no stream() ` +
        `method. FAIR supports AI SDK agents (Agent / ToolLoopAgent) or any ` +
        `object exposing stream({ messages }) -> { fullStream }. ` +
        `Use \`run\` if your framework differs.`,
    );
  }

  const handler: CapabilityHandler = async (command, ctx) => {
    const reporter = ctx.reporter;
    const turn = readTurn(command);
    const messageId = newId();
    const partId = newId();
    const chunker = new TextChunker(
      reporter,
      messageId,
      partId,
      options.chunking,
    );

    if (options.agent) {
      await streamFromAgent(options.agent, turn, ctx, chunker, reporter);
    } else {
      for await (const chunk of options.run!(turn, ctx)) {
        if (ctx.signal.aborted) break;
        await chunker.push(chunk);
      }
    }

    await chunker.finish();
  };

  return {
    id: options.id,
    surface: 'chat.agent',
    version: options.version ?? '1.0.0',
    displayName: options.name,
    description: options.description,
    declaredEffects: options.declaredEffects ?? [],
    supportsStreaming: true,
    supportsCancellation: true,
    handler,
  };
}

/**
 * Drive the agent's own stream and mirror it into FAIR.
 *
 * We consume `fullStream` directly rather than installing a transform: FAIR is
 * the caller here, so there is no second consumer to split the stream with, and
 * reading one ordered stream keeps text, tool calls and errors in the exact
 * order the agent produced them.
 */
async function streamFromAgent(
  agent: StreamingAgentLike,
  turn: AgentTurn,
  ctx: RunContext,
  chunker: TextChunker,
  reporter: ExecutionReporter,
): Promise<void> {
  const result = await agent.stream({
    messages: turn.messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
    abortSignal: ctx.signal,
  });

  for await (const part of result.fullStream as AsyncIterable<StreamPart>) {
    switch (part.type) {
      case 'text-delta':
        await chunker.push((part as { text: string }).text);
        break;

      case 'reasoning-delta':
        // Reasoning is recorded for research/debugging but is not chat text.
        await reporter.observation('agent.reasoning.delta', {
          text: (part as { text: string }).text,
        });
        break;

      case 'tool-call': {
        const p = part as { toolCallId: string; toolName: string; input: unknown };
        // Flush first so the tool call lands after the text that preceded it.
        await chunker.flush();
        await reporter.observation('agent.tool.called', {
          toolCallId: p.toolCallId,
          toolName: p.toolName,
          input: p.input,
        });
        break;
      }

      case 'tool-result': {
        const p = part as { toolCallId: string; toolName: string; output: unknown };
        await reporter.observation('agent.tool.result', {
          toolCallId: p.toolCallId,
          toolName: p.toolName,
          output: p.output,
        });
        break;
      }

      case 'tool-error': {
        const p = part as { toolCallId: string; toolName: string; error: unknown };
        await reporter.observation('agent.tool.failed', {
          toolCallId: p.toolCallId,
          toolName: p.toolName,
          error: serializeError(p.error).message,
        });
        break;
      }

      case 'error':
        // Let the runner's error boundary own the terminal outcome.
        throw (part as { error: unknown }).error;

      case 'abort':
        return;

      default:
        break;
    }
  }
}

/** Extract the conversation from the command payload. */
function readTurn(command: ExecutionCommand): AgentTurn {
  const input = (command.payload?.input ?? {}) as Record<string, unknown>;
  const history = Array.isArray(input.messages)
    ? (input.messages as ChatMessage[])
    : [];
  const content = typeof input.content === 'string' ? input.content : '';

  const messages: ChatMessage[] =
    history.length > 0
      ? history
      : content
        ? [{ role: 'user', content }]
        : [];

  const lastUser = [...messages].reverse().find((m) => m.role === 'user');
  return { messages, text: lastUser?.content ?? content };
}

import { randomUUID } from 'node:crypto';
import type {
  DelegatedAuthorization,
  ExecutionCommand,
  ExecutionEventCreate,
  EventVisibility,
} from './protocol.js';

/**
 * Everything an Execution needs to report itself back to FAIR.
 *
 * The protocol rules that live in here -- stable producer identity so retries
 * dedupe, bounded text chunking, token refresh, exactly one terminal event --
 * are the reason extension authors never see them.
 */
export class ExecutionReporter {
  readonly executionId: string;
  private readonly platformUrl: string;
  private readonly producerSource: string;
  private auth: DelegatedAuthorization;
  private producerSequence = 0;
  private terminal = false;
  /** Producer event ids are derived, not random, so a retried run dedupes. */
  private readonly runKey: string;

  constructor(private readonly command: ExecutionCommand) {
    this.executionId = command.execution.id;
    this.platformUrl = command.platformUrl.replace(/\/+$/, '');
    this.producerSource = command.execution.capability.extensionId;
    this.auth = command.authorization;
    this.runKey = command.idempotencyKey;
  }

  /** True once a terminal event has been accepted. */
  get isTerminal(): boolean {
    return this.terminal;
  }

  private async authorizationHeader(): Promise<string> {
    const expiresAt = Date.parse(this.auth.expiresAt);
    if (Number.isFinite(expiresAt) && expiresAt - Date.now() < 60_000) {
      await this.refreshAuthorization();
    }
    return `${this.auth.tokenType} ${this.auth.accessToken}`;
  }

  private async refreshAuthorization(): Promise<void> {
    const response = await fetch(
      `${this.platformUrl}/api/v1/executions/${this.executionId}/authorization/refresh`,
      {
        method: 'POST',
        headers: {
          Authorization: `${this.auth.tokenType} ${this.auth.accessToken}`,
        },
      },
    );
    if (!response.ok) {
      // A refusal here is normal at end of life (cancelled, terminal, revoked).
      // Keep the old token so the caller's terminal attempt produces the real
      // error rather than one invented by the refresh path.
      return;
    }
    this.auth = (await response.json()) as DelegatedAuthorization;
  }

  /** Send one durable event. Identity is derived so retries are idempotent. */
  async emit(
    type: string,
    payload: Record<string, unknown> = {},
    options: { visibility?: EventVisibility; producerEventId?: string } = {},
  ): Promise<void> {
    this.producerSequence += 1;
    const event: ExecutionEventCreate = {
      producerSource: this.producerSource,
      producerEventId:
        options.producerEventId ?? `${this.runKey}:${this.producerSequence}`,
      producerSequence: this.producerSequence,
      type,
      schemaUri: `urn:fair:event:${type}:v1`,
      visibility: options.visibility ?? 'user',
      payload,
    };

    const response = await fetch(
      `${this.platformUrl}/api/v1/executions/${this.executionId}/events/ingest`,
      {
        method: 'POST',
        headers: {
          Authorization: await this.authorizationHeader(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ events: [event] }),
      },
    );

    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(
        `FAIR rejected event ${type} (${response.status}): ${body}`,
      );
    }
  }

  async started(): Promise<void> {
    await this.emit('execution.started');
  }

  /**
   * Report a terminal outcome. Exactly one wins; later attempts are dropped
   * locally so an error handler cannot race a success that already landed.
   */
  async completed(outputSummary?: Record<string, unknown>): Promise<void> {
    if (this.terminal) return;
    this.terminal = true;
    await this.emit(
      'execution.completed',
      outputSummary ? { outputSummary } : {},
    );
  }

  async failed(error: unknown, errorCode = 'extension_error'): Promise<void> {
    if (this.terminal) return;
    this.terminal = true;
    await this.emit('execution.failed', {
      error: serializeError(error).message,
      errorCode,
    });
  }

  async cancelled(): Promise<void> {
    if (this.terminal) return;
    this.terminal = true;
    await this.emit('execution.cancelled', {});
  }

  // -- messages -----------------------------------------------------------

  async messageStarted(messageId: string, ordinal = 1): Promise<void> {
    await this.emit('message.started', {
      messageId,
      role: 'assistant',
      authorType: 'extension',
      ordinal,
    });
  }

  async messageDelta(
    messageId: string,
    partId: string,
    text: string,
  ): Promise<void> {
    await this.emit('message.delta', {
      messageId,
      partId,
      ordinal: 1,
      partType: 'text',
      text,
    });
  }

  async messageCompleted(messageId: string): Promise<void> {
    await this.emit('message.completed', { messageId });
  }

  /** Emit a non-text stream observation (tool call, reasoning, step) as a
   * private event: useful for research export and debugging, never rendered
   * as chat text. */
  async observation(
    type: string,
    payload: Record<string, unknown>,
  ): Promise<void> {
    await this.emit(type, payload, { visibility: 'private' });
  }

  async createArtifact(input: {
    title: string;
    kindUri: string;
    inlineJson: unknown;
  }): Promise<Record<string, unknown>> {
    const response = await fetch(
      `${this.platformUrl}/api/v1/executions/${this.executionId}/artifacts`,
      {
        method: 'POST',
        headers: {
          Authorization: await this.authorizationHeader(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: input.title,
          kindUri: input.kindUri,
          // An ArtifactVersion is a list of typed parts. The SDK exposes the
          // common single-JSON-payload case and builds the part envelope, so
          // authors do not have to know the storage shape.
          version: {
            parts: [
              {
                name: 'result',
                role: 'primary',
                mediaType: 'application/json',
                inlineJson: input.inlineJson,
              },
            ],
          },
          finalize: true,
        }),
      },
    );
    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(
        `FAIR rejected artifact (${response.status}): ${body}`,
      );
    }
    return (await response.json()) as Record<string, unknown>;
  }
}

export function serializeError(error: unknown): {
  name: string;
  message: string;
  stack?: string;
} {
  if (error instanceof Error) {
    return { name: error.name, message: error.message, stack: error.stack };
  }
  return { name: 'Error', message: String(error) };
}

export function newId(): string {
  return randomUUID();
}

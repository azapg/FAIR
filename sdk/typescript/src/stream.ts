import type { ExecutionReporter } from './reporter.js';

export interface ChunkingOptions {
  /** Flush at least this often while text keeps arriving. */
  flushIntervalMs?: number;
  /** Flush as soon as this many buffered characters accumulate. */
  maxChars?: number;
}

/**
 * Buffers model tokens into bounded durable chunks.
 *
 * Protocol 1 §5.2: one upstream token is NOT one durable HTTP event. At ~100ms
 * a chunk carries roughly a few words, which is below the threshold where
 * streaming text stops looking continuous, while cutting request volume by
 * about an order of magnitude versus per-token posting.
 *
 * Extension authors never construct this. They `yield` strings, or hand us an
 * AI SDK stream, and chunking happens here.
 */
export class TextChunker {
  private buffer: string[] = [];
  private bufferedChars = 0;
  private lastFlush = Date.now();
  private started = false;
  private readonly flushIntervalMs: number;
  private readonly maxChars: number;

  constructor(
    private readonly reporter: ExecutionReporter,
    private readonly messageId: string,
    private readonly partId: string,
    options: ChunkingOptions = {},
  ) {
    this.flushIntervalMs = options.flushIntervalMs ?? 100;
    this.maxChars = options.maxChars ?? 2048;
  }

  private async ensureStarted(): Promise<void> {
    if (this.started) return;
    this.started = true;
    await this.reporter.messageStarted(this.messageId);
  }

  async push(text: string): Promise<void> {
    if (!text) return;
    await this.ensureStarted();
    this.buffer.push(text);
    this.bufferedChars += text.length;
    const due = Date.now() - this.lastFlush >= this.flushIntervalMs;
    if (this.bufferedChars >= this.maxChars || due) {
      await this.flush();
    }
  }

  async flush(): Promise<void> {
    if (this.bufferedChars === 0) return;
    const text = this.buffer.join('');
    this.buffer = [];
    this.bufferedChars = 0;
    this.lastFlush = Date.now();
    await this.reporter.messageDelta(this.messageId, this.partId, text);
  }

  /** Flush anything buffered and close the message. Safe to call twice. */
  async finish(): Promise<void> {
    if (!this.started) return;
    await this.flush();
    await this.reporter.messageCompleted(this.messageId);
    this.started = false;
  }

  /** True once any text has been emitted for this message. */
  get hasStarted(): boolean {
    return this.started;
  }
}

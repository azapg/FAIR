import type { ExecutionCommand, Surface } from './protocol.js';
import type { ExecutionReporter } from './reporter.js';

/** JSON Schema, loosely typed. Authors rarely write one by hand. */
export type JsonSchema = Record<string, unknown>;

/**
 * What a capability handler is given. This is the whole author-facing surface
 * area for talking to FAIR -- there is deliberately no protocol object here.
 */
export interface RunContext {
  /** Aborted when FAIR cancels the Execution or the deadline passes. */
  readonly signal: AbortSignal;
  /** Course / assignment / submission this run is authorized for. */
  readonly scope: {
    courseId: string | null;
    assignmentId: string | null;
    submissionIds: string[];
  };
  readonly executionId: string;
  /** Escape hatch: raw event + artifact access. */
  readonly reporter: ExecutionReporter;
  /** Version-pinned inputs frozen before dispatch. */
  readonly artifacts: {
    list(): Array<{ artifactId: string; artifactVersionId: string }>;
    read(artifactId: string): Promise<unknown>;
    create(input: {
      title: string;
      kindUri: string;
      inlineJson: unknown;
    }): Promise<Record<string, unknown>>;
  };
  log(message: string, data?: Record<string, unknown>): Promise<void>;
}

export type CapabilityHandler = (
  command: ExecutionCommand,
  ctx: RunContext,
) => Promise<unknown>;

/** One registered capability, before it becomes manifest JSON. */
export interface CapabilitySpec {
  id: string;
  surface: Surface;
  version: string;
  displayName?: string;
  description?: string;
  /** Required for the `function` surface, e.g. "fair.rubric.generate@1". */
  contract?: string;
  inputSchema?: JsonSchema;
  outputSchema?: JsonSchema;
  declaredEffects: string[];
  supportsStreaming: boolean;
  supportsCancellation: boolean;
  supportsResume?: boolean;
  handler: CapabilityHandler;
}

export interface ExtensionOptions {
  id: string;
  name: string;
  version: string;
  capabilities: CapabilitySpec[];
  /** Defaults to FAIR_PLATFORM_URL. */
  platformUrl?: string;
  /** Defaults to FAIR_EXTENSION_SECRET. */
  secret?: string;
  /** Stable id for this runner process; defaults to the hostname. */
  runnerId?: string;
  /** How many Executions to run concurrently. */
  concurrency?: number;
}

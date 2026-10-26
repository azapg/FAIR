import { hostname } from 'node:os';
import type { ExecutionCommand, RunnerCommandLease } from './protocol.js';
import { ExecutionReporter, serializeError } from './reporter.js';
import type {
  CapabilitySpec,
  ExtensionOptions,
  RunContext,
} from './types.js';

/**
 * A running Extension.
 *
 * Delivery is runner mode: the process long-polls FAIR for work over an
 * outbound connection only. That means no inbound port, no tunnel, and no
 * webhook signature handling during development -- the same binary works on a
 * laptop behind NAT and on a server.
 */
export class Extension {
  private readonly platformUrl: string;
  private readonly secret: string;
  private readonly runnerId: string;
  private readonly concurrency: number;
  private readonly capabilities: Map<string, CapabilitySpec>;
  private running = false;
  private inFlight = 0;

  constructor(private readonly options: ExtensionOptions) {
    const platformUrl =
      options.platformUrl ?? process.env.FAIR_PLATFORM_URL ?? '';
    const secret = options.secret ?? process.env.FAIR_EXTENSION_SECRET ?? '';
    if (!platformUrl) {
      throw new Error(
        'No platform URL. Pass platformUrl or set FAIR_PLATFORM_URL.',
      );
    }
    if (!secret) {
      throw new Error(
        'No extension secret. Pass secret or set FAIR_EXTENSION_SECRET. ' +
          `Run \`fair ext bootstrap ${options.id}\` on the platform to issue one.`,
      );
    }
    this.platformUrl = platformUrl.replace(/\/+$/, '');
    this.secret = secret;
    this.runnerId = options.runnerId ?? `${hostname()}:${process.pid}`;
    this.concurrency = options.concurrency ?? 4;

    this.capabilities = new Map();
    for (const capability of options.capabilities) {
      if (this.capabilities.has(capability.id)) {
        throw new Error(`Duplicate capability id "${capability.id}"`);
      }
      this.capabilities.set(capability.id, capability);
    }
  }

  /** The manifest FAIR stores and pins. Derived, never hand-written. */
  manifest(): Record<string, unknown> {
    return {
      manifestVersion: '1',
      extensionId: this.options.id,
      displayName: this.options.name,
      version: this.options.version,
      deliveryMode: 'runner',
      capabilities: [...this.capabilities.values()].map((capability) => {
        const entry: Record<string, unknown> = {
          capabilityId: capability.id,
          surface: capability.surface,
          version: capability.version,
          supportsStreaming: capability.supportsStreaming,
          supportsCancellation: capability.supportsCancellation,
          declaredEffects: capability.declaredEffects,
        };
        if (capability.displayName) entry.displayName = capability.displayName;
        if (capability.description) entry.description = capability.description;
        if (capability.contract) entry.contract = capability.contract;
        if (capability.inputSchema) entry.inputSchema = capability.inputSchema;
        if (capability.outputSchema) {
          entry.outputSchema = capability.outputSchema;
        }
        return entry;
      }),
    };
  }

  private authHeaders(): Record<string, string> {
    // The Installation credential: it may only claim/ack commands and publish
    // this Extension's own manifest. It can never read educational data --
    // that authority arrives per-Execution in the command's token.
    return {
      'X-FAIR-Extension-Id': this.options.id,
      Authorization: `Bearer ${this.secret}`,
      'Content-Type': 'application/json',
    };
  }

  /** Publish the manifest so FAIR knows what this Extension can do. */
  async sync(): Promise<void> {
    const response = await fetch(
      `${this.platformUrl}/api/v1/extensions/self/manifest`,
      {
        method: 'PUT',
        headers: this.authHeaders(),
        body: JSON.stringify({ manifest: this.manifest() }),
      },
    );
    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(
        `Manifest sync failed (${response.status}): ${body}`,
      );
    }
  }

  /** Sync the manifest, then serve work until stopped. */
  async start(): Promise<void> {
    await this.sync();
    this.running = true;
    console.log(
      `[fair] ${this.options.id} v${this.options.version} ready ` +
        `(${this.capabilities.size} capabilities, runner ${this.runnerId})`,
    );
    for (const capability of this.capabilities.values()) {
      console.log(`[fair]   - ${capability.surface}: ${capability.id}`);
    }

    const shutdown = () => {
      console.log('[fair] shutting down after in-flight work');
      this.running = false;
    };
    process.once('SIGINT', shutdown);
    process.once('SIGTERM', shutdown);

    while (this.running) {
      if (this.inFlight >= this.concurrency) {
        await sleep(50);
        continue;
      }
      let lease: RunnerCommandLease | null = null;
      try {
        lease = await this.claim();
      } catch (error) {
        console.error('[fair] claim failed:', serializeError(error).message);
        await sleep(1000);
        continue;
      }
      if (!lease) continue;

      this.inFlight += 1;
      void this.handle(lease).finally(() => {
        this.inFlight -= 1;
      });
    }
  }

  private async claim(): Promise<RunnerCommandLease | null> {
    const response = await fetch(
      `${this.platformUrl}/api/v1/extensions/runner/commands/claim`,
      {
        method: 'POST',
        headers: this.authHeaders(),
        body: JSON.stringify({
          runnerId: this.runnerId,
          waitSeconds: 20,
          leaseSeconds: 120,
        }),
      },
    );
    if (response.status === 204) return null;
    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(`claim ${response.status}: ${body}`);
    }
    return (await response.json()) as RunnerCommandLease;
  }

  private async ack(commandId: string, leaseId: string): Promise<void> {
    await fetch(
      `${this.platformUrl}/api/v1/extensions/runner/commands/${commandId}/ack`,
      {
        method: 'POST',
        headers: this.authHeaders(),
        body: JSON.stringify({ leaseId }),
      },
    ).catch(() => undefined);
  }

  /**
   * Run one command to exactly one terminal outcome.
   *
   * Delivery is at-least-once, so this must be safe to run twice: producer
   * event ids are derived from the command's idempotency key, which makes a
   * redelivered command replay onto the same events instead of duplicating.
   */
  private async handle(lease: RunnerCommandLease): Promise<void> {
    const command = lease.command;
    const reporter = new ExecutionReporter(command);
    const controller = new AbortController();

    const deadline = Date.parse(command.execution.deadlineAt);
    const timer = Number.isFinite(deadline)
      ? setTimeout(
          () => controller.abort(),
          Math.max(0, deadline - Date.now()),
        )
      : undefined;

    try {
      if (command.command === 'cancel') {
        await reporter.cancelled();
        return;
      }

      const capability = this.capabilities.get(
        command.execution.capability.capabilityId,
      );
      if (!capability) {
        await reporter.failed(
          new Error(
            `This Extension has no capability "${command.execution.capability.capabilityId}"`,
          ),
          'unknown_capability',
        );
        return;
      }

      await reporter.started();
      const ctx = this.buildContext(command, reporter, controller.signal);
      const output = await capability.handler(command, ctx);

      if (controller.signal.aborted) {
        await reporter.cancelled();
      } else {
        await reporter.completed(
          output && typeof output === 'object'
            ? (output as Record<string, unknown>)
            : undefined,
        );
      }
    } catch (error) {
      const message = serializeError(error).message;
      console.error(`[fair] execution ${command.execution.id} failed:`, message);
      try {
        await reporter.failed(error);
      } catch (reportError) {
        // Reporting the failure failed too. FAIR's deadline watchdog will
        // expire the Execution; never let this escape and kill the runner.
        console.error(
          '[fair] could not report failure:',
          serializeError(reportError).message,
        );
      }
    } finally {
      if (timer) clearTimeout(timer);
      await this.ack(command.commandId, lease.leaseId);
    }
  }

  private buildContext(
    command: ExecutionCommand,
    reporter: ExecutionReporter,
    signal: AbortSignal,
  ): RunContext {
    const platformUrl = this.platformUrl;
    const executionId = command.execution.id;
    const token = `${command.authorization.tokenType} ${command.authorization.accessToken}`;

    return {
      signal,
      executionId,
      scope: command.execution.scope,
      reporter,
      artifacts: {
        list: () =>
          command.execution.artifacts.map((artifact) => ({
            artifactId: artifact.artifactId,
            artifactVersionId: artifact.artifactVersionId,
          })),
        read: async (artifactId: string) => {
          const response = await fetch(
            `${platformUrl}/api/v1/executions/${executionId}/artifacts/${artifactId}`,
            { headers: { Authorization: token } },
          );
          if (!response.ok) {
            throw new Error(`artifact read ${response.status}`);
          }
          return await response.json();
        },
        create: (input) => reporter.createArtifact(input),
      },
      log: async (message, data) => {
        await reporter.observation('extension.log', { message, ...data });
      },
    };
  }
}

export function createExtension(options: ExtensionOptions): Extension {
  return new Extension(options);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

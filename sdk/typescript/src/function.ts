import type { CapabilitySpec, JsonSchema, RunContext } from './types.js';

export interface FunctionCapabilityOptions<I = any, O = any> {
  /** A FAIR-owned contract id, e.g. "fair.rubric.generate@1". */
  contract: string;
  id?: string;
  name?: string;
  version?: string;
  declaredEffects?: string[];
  run: (input: I, ctx: RunContext) => Promise<O>;
}

/**
 * Implement a FAIR contract.
 *
 * The contract owns the input and output schemas and the UI placements, so
 * implementing one is enough to make a button appear wherever FAIR renders
 * that contract. Adding a new kind of function later is a new contract, not a
 * protocol change.
 */
export function functionCapability<I = any, O = any>(
  options: FunctionCapabilityOptions<I, O>,
): CapabilitySpec {
  const id = options.id ?? options.contract.replace(/@\d+$/, '');
  return {
    id,
    surface: 'function',
    contract: options.contract,
    version: options.version ?? '1.0.0',
    displayName: options.name,
    declaredEffects: options.declaredEffects ?? [],
    supportsStreaming: false,
    supportsCancellation: false,
    handler: async (command, ctx) => {
      const input = (command.payload?.input ?? {}) as I;
      return await options.run(input, ctx);
    },
  };
}

export interface FlowStepOptions<I = any, O = any> {
  id: string;
  name?: string;
  version?: string;
  inputSchema?: JsonSchema;
  outputSchema?: JsonSchema;
  declaredEffects?: string[];
  run: (input: I, ctx: RunContext) => Promise<O>;
}

/**
 * A node a Flow can pin and re-run.
 *
 * Flow steps are plain functions on purpose: a reproducible benchmark wants a
 * deterministic input -> output contract, not a conversation.
 */
export function flowStep<I = any, O = any>(
  options: FlowStepOptions<I, O>,
): CapabilitySpec {
  return {
    id: options.id,
    surface: 'flow.step',
    version: options.version ?? '1.0.0',
    displayName: options.name,
    inputSchema: options.inputSchema,
    outputSchema: options.outputSchema,
    declaredEffects: options.declaredEffects ?? [],
    supportsStreaming: false,
    supportsCancellation: false,
    handler: async (command, ctx) => {
      // A Flow step receives the node envelope FAIR builds: the flow input,
      // the previous step's output, and this node's own configured input.
      const payload = (command.payload?.input ?? {}) as Record<string, unknown>;
      const input = {
        ...(payload.nodeInput as Record<string, unknown> | undefined),
        flowInput: payload.flowInput,
        previousOutput: payload.previousOutput,
      } as I;
      return await options.run(input, ctx);
    },
  };
}

/**
 * Wire types for FAIR Extension Execution Protocol 1.
 *
 * These mirror `specs/extension-execution-protocol.md`. Extension authors are
 * not expected to import anything from this file -- it exists so the transport
 * can be typed, and so a reader can see exactly what crosses the boundary.
 */

export const PROTOCOL_VERSION = '1';

/** One of the three places a Capability can plug into FAIR. */
export type Surface = 'chat.agent' | 'function' | 'flow.step';

export interface CapabilityPin {
  definitionId: string;
  capabilityId: string;
  version: string;
  installationId: string;
  extensionId: string;
}

export interface ExecutionScope {
  courseId: string | null;
  assignmentId: string | null;
  submissionIds: string[];
}

export interface ExecutionInputArtifact {
  artifactId: string;
  artifactVersionId: string;
  kindUri?: string;
  title?: string | null;
  mediaType?: string | null;
}

export interface ExecutionDescriptor {
  id: string;
  rootExecutionId: string;
  parentExecutionId: string | null;
  attempt: number;
  kind: string;
  capability: CapabilityPin;
  scope: ExecutionScope;
  deadlineAt: string;
  artifacts: ExecutionInputArtifact[];
}

export interface DelegatedAuthorization {
  tokenType: string;
  accessToken: string;
  expiresAt: string;
  scopes: string[];
}

export type CommandKind = 'start' | 'resume' | 'cancel';

export interface ExecutionCommand {
  protocolVersion: string;
  commandId: string;
  idempotencyKey: string;
  command: CommandKind;
  issuedAt: string;
  expiresAt: string;
  platformUrl: string;
  execution: ExecutionDescriptor;
  authorization: DelegatedAuthorization;
  payload: { input?: Record<string, unknown>; [key: string]: unknown };
  traceparent?: string;
}

export interface RunnerCommandLease {
  leaseId: string;
  leaseExpiresAt: string;
  command: ExecutionCommand;
}

export type EventVisibility = 'user' | 'private' | 'operator';

export interface ExecutionEventCreate {
  producerSource: string;
  producerEventId: string;
  producerSequence: number;
  type: string;
  schemaUri: string;
  visibility: EventVisibility;
  payload: Record<string, unknown>;
  occurredAt?: string;
  traceId?: string | null;
  spanId?: string | null;
}

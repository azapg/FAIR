/** The stable `/api/v1` Execution event contract used by the frontend. */

export type EventVisibility = "user" | "operator" | "private";
export type ExecutionStatus =
  | "queued"
  | "running"
  | "waiting"
  | "completed"
  | "failed"
  | "cancelled"
  | "expired";

export type ExecutionEventCreate = {
  producerSource: string;
  producerEventId: string;
  producerSequence?: number;
  type: string;
  schemaUri: string;
  occurredAt?: string;
  visibility?: EventVisibility;
  durability?: "durable";
  payload: Record<string, unknown>;
  parentEventId?: string;
  traceId?: string;
  spanId?: string;
};

export type ExecutionEvent = ExecutionEventCreate & {
  id: string;
  executionId: string;
  sequence: number;
  occurredAt: string;
  receivedAt: string;
};

export type Interaction = {
  id: string;
  executionId: string;
  kind: string;
  schema: Record<string, unknown>;
  message: string;
  choices: Array<Record<string, unknown>> | null;
  targetUrl: string | null;
  status: "pending" | "resolved" | "declined" | "cancelled" | "expired";
  requestedByExtensionInstallationId: string | null;
  expiresAt: string | null;
  resolvedByUserId: string | null;
  response: Record<string, unknown> | null;
  resolvedAt: string | null;
  createdAt: string;
};

export type ArtifactPart = {
  id: string;
  artifactVersionId: string;
  ordinal: number;
  name: string;
  role: string;
  mediaType: string;
  schemaUri: string | null;
  storageUri: string | null;
  inlineJson: Record<string, unknown> | null;
  contentHash: string | null;
  sizeBytes: number | null;
  annotations: Record<string, unknown> | null;
  hashAlgorithm: string | null;
  createdAt: string;
};

export type ArtifactVersion = {
  id: string;
  artifactId: string;
  ordinal: number;
  state: "draft" | "finalized" | "abandoned";
  mediaType: string | null;
  schemaUri: string | null;
  metadata: Record<string, unknown>;
  createdByUserId: string | null;
  createdByExtensionInstallationId: string | null;
  producingExecutionId: string | null;
  hashAlgorithm: string | null;
  contentHash: string | null;
  sizeBytes: number | null;
  provenance: Record<string, unknown>;
  supersedesVersionId: string | null;
  createdAt: string;
  finalizedAt: string | null;
  abandonedAt: string | null;
  parts: ArtifactPart[];
  links: ArtifactLink[];
};

export type ArtifactLink = {
  id: string;
  artifactVersionId: string;
  relationship:
    | "input"
    | "output"
    | "evidence"
    | "derived_from"
    | "attached_to"
    | "citation"
    | "preview";
  targetType: string;
  targetId: string;
  metadata: Record<string, unknown> | null;
  createdByExecutionId: string | null;
  createdAt: string;
  retractedAt: string | null;
};

export type Artifact = {
  id: string;
  title: string;
  artifactType: string;
  kindUri: string | null;
  description: string | null;
  ownerUserId: string | null;
  creatorId: string;
  sensitivity: string | null;
  accessPolicy: Record<string, unknown> | null;
  currentVersionId: string | null;
  createdAt: string;
  updatedAt: string;
  versions: ArtifactVersion[];
};

const terminalStatuses = new Set<ExecutionStatus>([
  "completed",
  "failed",
  "cancelled",
  "expired",
]);

export function isTerminalExecutionStatus(status: string): status is ExecutionStatus {
  return terminalStatuses.has(status as ExecutionStatus);
}

export function eventCursor(event: Pick<ExecutionEvent, "sequence">): string {
  return String(event.sequence);
}

/** Validate the untrusted JSON delivered by REST/SSE before projecting it in UI state. */
export function parseExecutionEvent(value: unknown): ExecutionEvent {
  if (!value || typeof value !== "object") {
    throw new Error("Execution event must be an object");
  }
  const event = value as Partial<ExecutionEvent>;
  if (
    typeof event.id !== "string" ||
    typeof event.executionId !== "string" ||
    typeof event.sequence !== "number" ||
    !Number.isInteger(event.sequence) ||
    event.sequence < 1 ||
    typeof event.producerSource !== "string" ||
    typeof event.producerEventId !== "string" ||
    typeof event.type !== "string" ||
    typeof event.schemaUri !== "string" ||
    typeof event.occurredAt !== "string" ||
    typeof event.receivedAt !== "string" ||
    !event.payload ||
    typeof event.payload !== "object" ||
    Array.isArray(event.payload)
  ) {
    throw new Error("Invalid FAIR Execution event envelope");
  }
  return event as ExecutionEvent;
}

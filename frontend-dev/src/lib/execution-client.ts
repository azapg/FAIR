import api from "@/lib/api";
import {
  eventCursor,
  ExecutionEvent,
  ExecutionEventCreate,
  Artifact,
  ArtifactLink,
  ArtifactVersion,
  Interaction,
  parseExecutionEvent,
} from "@/lib/execution-contract";

export type V2Thread = {
  id: string;
  ownerUserId: string;
  title: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type V2Turn = {
  id: string;
  threadId: string;
  executionId: string;
  userMessageId: string;
  ordinal: number;
  clientRequestId: string;
  status: string;
  createdAt: string;
  completedAt: string | null;
};

export async function createExecutionThread(title = "Live chat"): Promise<V2Thread> {
  const response = await api.post<V2Thread>("/v1/threads", { title });
  return response.data;
}

export async function createExecutionTurn(
  threadId: string,
  input: { content: string; target?: string; capabilityId?: string; clientRequestId?: string },
): Promise<V2Turn> {
  const response = await api.post<V2Turn>(
    `/v1/threads/${threadId}/turns`,
    input,
  );
  return response.data;
}

export async function getExecutionEvents(
  executionId: string,
  afterSequence = 0,
): Promise<ExecutionEvent[]> {
  const response = await api.get<unknown[]>(
    `/v1/executions/${executionId}/events`,
    { params: { after_sequence: afterSequence } },
  );
  return response.data.map(parseExecutionEvent);
}

export async function appendExecutionEvents(
  executionId: string,
  events: ExecutionEventCreate[],
): Promise<ExecutionEvent[]> {
  const response = await api.post<unknown[]>(
    `/v1/executions/${executionId}/events`,
    { events },
  );
  return response.data.map(parseExecutionEvent);
}

export async function listExecutionInteractions(
  executionId: string,
): Promise<Interaction[]> {
  const response = await api.get<Interaction[]>(
    `/v1/executions/${executionId}/interactions`,
  );
  return response.data;
}

export async function resolveInteraction(
  interactionId: string,
  input: {
    status?: "resolved" | "declined";
    response?: Record<string, unknown> | null;
    clientRequestId?: string;
  },
): Promise<Interaction> {
  const response = await api.post<Interaction>(
    `/v1/interactions/${interactionId}/resolve`,
    input,
  );
  return response.data;
}

export async function createArtifact(input: {
  title: string;
  kindUri?: string;
  description?: string | null;
  sensitivity?: string | null;
  accessPolicy?: Record<string, unknown> | null;
}): Promise<Artifact> {
  const response = await api.post<Artifact>("/v1/artifacts", input);
  return response.data;
}

export async function getArtifact(artifactId: string): Promise<Artifact> {
  const response = await api.get<Artifact>(`/v1/artifacts/${artifactId}`);
  return response.data;
}

export async function createArtifactVersion(
  artifactId: string,
  input: {
    mediaType?: string | null;
    schemaUri?: string | null;
    metadata?: Record<string, unknown>;
    provenance?: Record<string, unknown>;
    supersedesVersionId?: string | null;
    parts: Array<{
      name: string;
      role: string;
      mediaType: string;
      schemaUri?: string | null;
      storageUri?: string;
      inlineJson?: Record<string, unknown>;
      contentHash?: string;
      sizeBytes?: number;
      annotations?: Record<string, unknown>;
    }>;
  },
): Promise<ArtifactVersion> {
  const response = await api.post<ArtifactVersion>(
    `/v1/artifacts/${artifactId}/versions`,
    input,
  );
  return response.data;
}

export async function finalizeArtifactVersion(
  versionId: string,
): Promise<ArtifactVersion> {
  const response = await api.post<ArtifactVersion>(
    `/v1/artifact-versions/${versionId}/finalize`,
  );
  return response.data;
}

export async function listArtifactLinks(
  versionId: string,
): Promise<ArtifactLink[]> {
  const response = await api.get<ArtifactLink[]>(
    `/v1/artifact-versions/${versionId}/links`,
  );
  return response.data;
}

export async function createArtifactLink(
  versionId: string,
  input: {
    relationship: ArtifactLink["relationship"];
    targetType: string;
    targetId: string;
    metadata?: Record<string, unknown> | null;
    createdByExecutionId?: string | null;
  },
): Promise<ArtifactLink> {
  const response = await api.post<ArtifactLink>(
    `/v1/artifact-versions/${versionId}/links`,
    input,
  );
  return response.data;
}

export { eventCursor };

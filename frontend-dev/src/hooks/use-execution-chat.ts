import { useCallback, useEffect, useRef, useState } from "react";
import {
  createExecutionThread,
  createExecutionTurn,
  resolveInteraction as resolveInteractionRequest,
} from "@/lib/execution-client";
import { streamSse } from "@/lib/sse-stream";
import {
  ExecutionEvent,
  ExecutionStatus,
  Interaction,
  parseExecutionEvent,
} from "@/lib/execution-contract";
import type { Message } from "@/lib/chat-contract";

type LiveStatus = ExecutionStatus | "idle" | "streaming" | "error";
type JsonRecord = Record<string, unknown>;

export type ExecutionChatProjection = {
  messages: Message[];
  interactions: Interaction[];
  status: LiveStatus;
};

export const initialExecutionChatProjection: ExecutionChatProjection = {
  messages: [],
  interactions: [],
  status: "idle",
};

// FAIR normalizes standard event payloads to camel-case before serving them,
// so clients read one shape regardless of what an Extension emitted.
function payloadValue(payload: JsonRecord, field: string): unknown {
  return payload[field];
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : {};
}

function messageTimestamp(event: ExecutionEvent): string {
  return new Date(event.occurredAt).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function interactionFromEvent(event: ExecutionEvent): Interaction {
  const payload = event.payload;
  const rawChoices = payloadValue(payload, "choices");
  const choices = Array.isArray(rawChoices)
    ? rawChoices.map((choice) => {
        const item = asRecord(choice);
        const value = asString(item.value, asString(item.label));
        return { label: asString(item.label, value), value };
      })
    : null;

  return {
    id: asString(payloadValue(payload, "interactionId")),
    executionId: event.executionId,
    kind: asString(payloadValue(payload, "kind"), "interaction"),
    schema: asRecord(payloadValue(payload, "schema")),
    message: asString(payloadValue(payload, "message"), "Please provide a response."),
    choices,
    targetUrl: payloadValue(payload, "targetUrl") as string | null,
    status: "pending",
    requestedByExtensionInstallationId: null,
    expiresAt: (payloadValue(payload, "expiresAt") as string | null) ?? null,
    resolvedByUserId: null,
    response: null,
    resolvedAt: null,
    createdAt: event.occurredAt,
  };
}

export function projectExecutionEvent(
  current: ExecutionChatProjection,
  event: ExecutionEvent,
): ExecutionChatProjection {
  const payload = event.payload;

  if (event.type.startsWith("execution.")) {
    const next = event.type.slice("execution.".length);
    if (["queued", "running", "waiting", "completed", "failed", "cancelled", "expired"].includes(next)) {
      return current.status === next
        ? current
        : { ...current, status: next as ExecutionStatus };
    }
  }

  if (event.type === "message.started") {
    const id = asString(payloadValue(payload, "messageId"));
    if (current.messages.some((message) => message.id === id)) return current;
    const role = asString(payloadValue(payload, "role"), "assistant");
    return {
      ...current,
      messages: [
        ...current.messages,
        {
          id,
          role: role === "user" ? "user" : "assistant",
          senderName: asString(payloadValue(payload, "senderName"), "Assistant"),
          timestamp: messageTimestamp(event),
          content: "",
          events: [],
        },
      ],
    };
  }

  if (event.type === "message.delta") {
    const id = asString(payloadValue(payload, "messageId"));
    const delta = asString(payloadValue(payload, "text"), asString(payloadValue(payload, "delta")));
    const messageIndex = current.messages.findIndex((message) => message.id === id);
    if (messageIndex < 0) {
      return {
        ...current,
        messages: [
          ...current.messages,
          {
            id,
            role: "assistant",
            senderName: "Assistant",
            timestamp: messageTimestamp(event),
            content: delta,
            events: [],
          },
        ],
      };
    }
    const messages = current.messages.slice();
    const message = messages[messageIndex];
    messages[messageIndex] = { ...message, content: `${message.content}${delta}` };
    return { ...current, messages };
  }

  if (event.type === "interaction.requested") {
    const interaction = interactionFromEvent(event);
    return {
      ...current,
      interactions: [
        ...current.interactions.filter((item) => item.id !== interaction.id),
        interaction,
      ],
      status: "waiting",
    };
  }

  if (event.type === "interaction.resolved") {
    const id = asString(payloadValue(payload, "interactionId"));
    const resolvedStatus = asString(payloadValue(payload, "status"), "resolved");
    const interactions = current.interactions.map((interaction) =>
      interaction.id === id
        ? {
            ...interaction,
            status: resolvedStatus as Interaction["status"],
            response: asRecord(payloadValue(payload, "response")),
            resolvedAt: event.occurredAt,
          }
        : interaction,
    );
    return interactions.every((interaction, index) => interaction === current.interactions[index])
      ? current
      : { ...current, interactions };
  }

  if (event.type === "artifact.created") {
    const artifactId = asString(payloadValue(payload, "artifactVersionId"));
    let messageIndex = -1;
    for (let index = current.messages.length - 1; index >= 0; index -= 1) {
      if (current.messages[index].role === "assistant") {
        messageIndex = index;
        break;
      }
    }
    if (messageIndex < 0) return current;
    const messages = current.messages.slice();
    const message = messages[messageIndex];
    messages[messageIndex] = {
      ...message,
      events: [
        ...(message.events ?? []),
        {
          type: "artifact_update",
          action: "create",
          artifactName: artifactId || "artifact",
        },
      ],
    };
    return { ...current, messages };
  }

  return current;
}

export function useExecutionChat(capabilityDefinitionId?: string) {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [projection, setProjection] = useState<ExecutionChatProjection>(initialExecutionChatProjection);
  const [error, setError] = useState<string | null>(null);
  const sequenceRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  useEffect(() => stop, [stop]);

  const applyEvent = useCallback((event: ExecutionEvent) => {
    sequenceRef.current = Math.max(sequenceRef.current, event.sequence);
    setProjection((current) => projectExecutionEvent(current, event));
  }, []);

  const streamExecution = useCallback(async (id: string, afterSequence = 0) => {
    stop();
    const controller = new AbortController();
    abortRef.current = controller;
    setProjection((current) => ({ ...current, status: "streaming" }));
    setError(null);
    try {
      await streamSse(
        `/api/v1/executions/${id}/stream?after_sequence=${afterSequence}`,
        {
          signal: controller.signal,
          timeoutMs: 120000,
          onEvent: (sseEvent) => {
            try {
              const parsed = parseExecutionEvent(JSON.parse(sseEvent.data));
              applyEvent(parsed);
            } catch (parseError) {
              setError(parseError instanceof Error ? parseError.message : "Invalid Execution event");
            }
          },
        },
      );
    } catch (streamError) {
      if (!controller.signal.aborted) {
        setProjection((current) => ({ ...current, status: "error" }));
        setError(streamError instanceof Error ? streamError.message : "Execution stream failed");
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [applyEvent, stop]);

  const send = useCallback(async (content: string) => {
    if (!content.trim() || projection.status === "streaming") return;
    if (!capabilityDefinitionId) {
      setError("Select an installed agent capability before sending a message.");
      return;
    }
    setError(null);
    try {
      const activeThreadId = threadId ?? (await createExecutionThread()).id;
      if (!threadId) setThreadId(activeThreadId);
      const turn = await createExecutionTurn(activeThreadId, {
        content: content.trim(),
        capabilityDefinitionId,
      });
      setExecutionId(turn.executionId);
      setProjection((current) => ({
        ...current,
        messages: [
          ...current.messages,
          {
            id: turn.userMessageId,
            role: "user",
            senderName: "You",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            content: content.trim(),
          },
        ],
      }));
      await streamExecution(turn.executionId, 0);
    } catch (sendError) {
      setProjection((current) => ({ ...current, status: "error" }));
      setError(sendError instanceof Error ? sendError.message : "Unable to start Execution");
    }
  }, [capabilityDefinitionId, projection.status, streamExecution, threadId]);

  const resolve = useCallback(async (interactionId: string, response: string) => {
    const resolved = await resolveInteractionRequest(interactionId, {
      response: { value: response },
      clientRequestId: `ui-${interactionId}-${response}`,
    });
    setProjection((current) => ({
      ...current,
      interactions: current.interactions.map((interaction) =>
        interaction.id === resolved.id ? resolved : interaction,
      ),
    }));
  }, []);

  const reset = useCallback(() => {
    stop();
    setThreadId(null);
    setExecutionId(null);
    setProjection(initialExecutionChatProjection);
    setError(null);
    sequenceRef.current = 0;
  }, [stop]);

  return {
    threadId,
    executionId,
    messages: projection.messages,
    interactions: projection.interactions,
    pendingInteraction: projection.interactions.find((interaction) => interaction.status === "pending") ?? null,
    status: projection.status,
    error,
    sequence: sequenceRef.current,
    send,
    resolve,
    reset,
    stop,
  };
}

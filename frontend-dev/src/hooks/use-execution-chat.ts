import { useCallback, useRef, useState } from "react";
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
import { Message } from "@/store/chat-store";

type LiveStatus = ExecutionStatus | "idle" | "streaming" | "error";
type JsonRecord = Record<string, unknown>;

function payloadValue(payload: JsonRecord, field: string): unknown {
  if (field in payload) return payload[field];
  const camel = field.split("_")[0] + field
    .split("_")
    .slice(1)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
  return payload[camel];
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
    id: asString(payloadValue(payload, "interaction_id")),
    executionId: event.executionId,
    kind: asString(payloadValue(payload, "kind"), "interaction"),
    schema: asRecord(payloadValue(payload, "schema")),
    message: asString(payloadValue(payload, "message"), "Please provide a response."),
    choices,
    targetUrl: payloadValue(payload, "target_url") as string | null,
    status: "pending",
    requestedByExtensionInstallationId: null,
    expiresAt: (payloadValue(payload, "expires_at") as string | null) ?? null,
    resolvedByUserId: null,
    response: null,
    resolvedAt: null,
    createdAt: event.occurredAt,
  };
}

export function useExecutionChat() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const sequenceRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const applyEvent = useCallback((event: ExecutionEvent) => {
    sequenceRef.current = Math.max(sequenceRef.current, event.sequence);
    const payload = event.payload;

    if (event.type.startsWith("execution.")) {
      const next = event.type.slice("execution.".length);
      if (["queued", "running", "waiting", "completed", "failed", "cancelled", "expired"].includes(next)) {
        setStatus(next as ExecutionStatus);
      }
    }

    if (event.type === "message.started") {
      const id = asString(payloadValue(payload, "message_id"));
      const role = asString(payloadValue(payload, "role"), "assistant");
      setMessages((current) => {
        if (current.some((message) => message.id === id)) return current;
        return [
          ...current,
          {
            id,
            role: role === "user" ? "user" : "assistant",
            senderName: asString(payloadValue(payload, "sender_name"), "Assistant"),
            timestamp: messageTimestamp(event),
            content: "",
            events: [],
          },
        ];
      });
    }

    if (event.type === "message.delta") {
      const id = asString(payloadValue(payload, "message_id"));
      const delta = asString(payloadValue(payload, "text"), asString(payloadValue(payload, "delta")));
      setMessages((current) => {
        if (!current.some((message) => message.id === id)) {
          return [
            ...current,
            {
              id,
              role: "assistant",
              senderName: "Assistant",
              timestamp: messageTimestamp(event),
              content: delta,
              events: [],
            },
          ];
        }
        return current.map((message) =>
          message.id === id
            ? { ...message, content: `${message.content}${delta}` }
            : message,
        );
      });
    }

    if (event.type === "interaction.requested") {
      const interaction = interactionFromEvent(event);
      setInteractions((current) => [
        ...current.filter((item) => item.id !== interaction.id),
        interaction,
      ]);
      setStatus("waiting");
    }

    if (event.type === "interaction.resolved") {
      const id = asString(payloadValue(payload, "interaction_id"));
      const resolvedStatus = asString(payloadValue(payload, "status"), "resolved");
      setInteractions((current) =>
        current.map((interaction) =>
          interaction.id === id
            ? {
                ...interaction,
                status: resolvedStatus as Interaction["status"],
                response: asRecord(payloadValue(payload, "response")),
                resolvedAt: event.occurredAt,
              }
            : interaction,
        ),
      );
    }

    if (event.type === "artifact.created") {
      const artifactId = asString(payloadValue(payload, "artifact_version_id"));
      setMessages((current) => {
        const index = [...current].reverse().findIndex((message) => message.role === "assistant");
        if (index < 0) return current;
        const messageIndex = current.length - 1 - index;
        return current.map((message, candidateIndex) =>
          candidateIndex === messageIndex
            ? {
                ...message,
                events: [
                  ...(message.events ?? []),
                  {
                    type: "artifact_update",
                    action: "create",
                    artifactName: artifactId || "artifact",
                  },
                ],
              }
            : message,
        );
      });
    }
  }, []);

  const streamExecution = useCallback(async (id: string, afterSequence = 0) => {
    stop();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("streaming");
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
        setStatus("error");
        setError(streamError instanceof Error ? streamError.message : "Execution stream failed");
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [applyEvent, stop]);

  const send = useCallback(async (content: string) => {
    if (!content.trim() || status === "streaming") return;
    setError(null);
    try {
      const activeThreadId = threadId ?? (await createExecutionThread()).id;
      if (!threadId) setThreadId(activeThreadId);
      const turn = await createExecutionTurn(activeThreadId, { content: content.trim() });
      setExecutionId(turn.executionId);
      setMessages((current) => [
        ...current,
        {
          id: turn.userMessageId,
          role: "user",
          senderName: "You",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          content: content.trim(),
        },
      ]);
      await streamExecution(turn.executionId, 0);
    } catch (sendError) {
      setStatus("error");
      setError(sendError instanceof Error ? sendError.message : "Unable to start Execution");
    }
  }, [status, streamExecution, threadId]);

  const resolve = useCallback(async (interactionId: string, response: string) => {
    const resolved = await resolveInteractionRequest(interactionId, {
      response: { value: response },
      clientRequestId: `ui-${interactionId}-${response}`,
    });
    setInteractions((current) =>
      current.map((interaction) => (interaction.id === resolved.id ? resolved : interaction)),
    );
  }, []);

  const reset = useCallback(() => {
    stop();
    setThreadId(null);
    setExecutionId(null);
    setMessages([]);
    setInteractions([]);
    setStatus("idle");
    setError(null);
    sequenceRef.current = 0;
  }, [stop]);

  return {
    threadId,
    executionId,
    messages,
    interactions,
    pendingInteraction: interactions.find((interaction) => interaction.status === "pending") ?? null,
    status,
    error,
    sequence: sequenceRef.current,
    send,
    resolve,
    reset,
    stop,
  };
}

import { describe, expect, it } from "vitest";

import {
  initialExecutionChatProjection,
  projectExecutionEvent,
} from "./use-execution-chat";
import type { ExecutionEvent } from "@/lib/execution-contract";

function event(type: string, payload: Record<string, unknown>, sequence: number): ExecutionEvent {
  return {
    id: `event-${sequence}`,
    executionId: "execution-1",
    sequence,
    producerSource: "test",
    producerEventId: `producer-${sequence}`,
    type,
    schemaUri: "https://fair.example/events/test",
    occurredAt: "2026-07-18T12:00:00Z",
    receivedAt: "2026-07-18T12:00:00Z",
    payload,
  };
}

describe("projectExecutionEvent", () => {
  it("preserves historical message identity while appending deltas", () => {
    const withHistorical = projectExecutionEvent(
      initialExecutionChatProjection,
      event("message.started", { message_id: "historical", role: "assistant" }, 1),
    );
    const withCurrent = projectExecutionEvent(
      withHistorical,
      event("message.started", { message_id: "current", role: "assistant" }, 2),
    );
    const projected = projectExecutionEvent(
      withCurrent,
      event("message.delta", { message_id: "current", text: "Hello" }, 3),
    );

    expect(projected.messages[0]).toBe(withCurrent.messages[0]);
    expect(projected.messages[1].content).toBe("Hello");
  });

  it("projects interactions and artifacts in event order", () => {
    const withMessage = projectExecutionEvent(
      initialExecutionChatProjection,
      event("message.started", { message_id: "assistant", role: "assistant" }, 1),
    );
    const waiting = projectExecutionEvent(
      withMessage,
      event("interaction.requested", {
        interaction_id: "interaction-1",
        message: "Continue?",
        choices: [{ label: "Yes", value: "yes" }],
      }, 2),
    );
    const withArtifact = projectExecutionEvent(
      waiting,
      event("artifact.created", { artifact_version_id: "artifact-version-1" }, 3),
    );

    expect(waiting.status).toBe("waiting");
    expect(waiting.interactions[0]).toMatchObject({ id: "interaction-1", status: "pending" });
    expect(withArtifact.messages[0].events).toEqual([
      expect.objectContaining({ type: "artifact_update", artifactName: "artifact-version-1" }),
    ]);
  });
});

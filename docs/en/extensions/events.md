---
title: Events and streaming
description: Report progress once and let FAIR replay it to product clients.
---

An **Event** is a durable update from an Execution. Extensions send Events to FAIR; browsers stream the accepted Events from FAIR.

```text
Extension -> Event ingest -> durable log -> SSE -> browser
```

This keeps one source of truth for retries, reconnects, audits, and research export.

## Send Events

```text
POST /api/v1/executions/{executionId}/events/ingest
Authorization: Bearer {execution token}
```

A batch contains 1-100 Events. Each Event has a stable `producerSource` and `producerEventId`. Resend the same identity and content when a response is lost. FAIR returns `409` if the identity is reused with different content.

## Common Event types

| Purpose | Event types |
| --- | --- |
| lifecycle | `execution.started`, `execution.waiting`, `execution.completed`, `execution.failed`, `execution.cancelled` |
| streamed message | `message.started`, `message.part.created`, `message.delta`, `message.completed` |
| user input | `interaction.requested` |
| output lineage | `artifact.created` |

Custom research Events are allowed when they use a stable `schemaUri`.

## Stream to clients

```text
GET /api/v1/executions/{executionId}/stream
Last-Event-ID: {last sequence}
```

FAIR replays from the durable sequence. User streams exclude `private` and `operator` Events.

## Streaming tokens

Send bounded text chunks, not one HTTP request per model token. The internal Python reference flushes after 100 ms or 2,048 characters by default.

<Warning>
TODO: Publish a stable high-level chat stream API in the standalone SDKs. Raw Event ingest and replayable SSE are implemented.
</Warning>

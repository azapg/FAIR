from __future__ import annotations

import asyncio
from datetime import datetime
from datetime import timedelta, timezone
from typing import Any, AsyncIterable
from uuid import UUID, uuid4

import httpx

from fair_platform.extension_sdk.contracts.events import (
    ExecutionEventBatch,
    ExecutionEventCreate,
    ExecutionEventRead,
)
from fair_platform.extension_sdk.contracts.protocol import (
    DelegatedExecutionAuthorization,
    ExecutionCommand,
    ToolInvocationRead,
    ToolInvocationRequest,
)


class ExecutionReporter:
    """Small framework-agnostic reporter for FAIR Execution events."""

    def __init__(
        self,
        *,
        command: ExecutionCommand,
        timeout: float = 20.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.command = command
        self.execution_id = str(command.execution.id)
        self._producer_source = command.execution.capability.extension_id
        self._authorization_headers = {
            "Authorization": (
                f"{command.authorization.token_type} "
                f"{command.authorization.access_token}"
            )
        }
        self._authorization_expires_at = command.authorization.expires_at
        self._client = client or httpx.AsyncClient(
            base_url=str(command.platform_url).rstrip("/"),
            headers=self._authorization_headers,
            timeout=timeout,
        )
        self._owns_client = client is None
        self._producer_sequence = 0

    async def __aenter__(self) -> "ExecutionReporter":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def refresh_authorization(self) -> None:
        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/authorization/refresh",
            headers=self._authorization_headers,
        )
        response.raise_for_status()
        authorization = DelegatedExecutionAuthorization.model_validate(response.json())
        self._authorization_headers = {
            "Authorization": f"{authorization.token_type} {authorization.access_token}"
        }
        self._authorization_expires_at = authorization.expires_at

    async def _ensure_authorization(self) -> None:
        expires_at = self._authorization_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc) + timedelta(seconds=60):
            await self.refresh_authorization()

    async def emit_event(self, event: ExecutionEventCreate) -> ExecutionEventRead:
        """Send one already-built event, preserving its retry identity."""

        await self._ensure_authorization()
        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/events/ingest",
            headers=self._authorization_headers,
            json=ExecutionEventBatch(events=[event]).model_dump(
                by_alias=True, mode="json"
            ),
        )
        response.raise_for_status()
        accepted = response.json()
        if not isinstance(accepted, list) or len(accepted) != 1:
            raise RuntimeError("FAIR returned an invalid single-event response")
        return ExecutionEventRead.model_validate(accepted[0])

    async def emit_batch(
        self, events: list[ExecutionEventCreate]
    ) -> list[ExecutionEventRead]:
        if not events:
            return []
        await self._ensure_authorization()
        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/events/ingest",
            headers=self._authorization_headers,
            json=ExecutionEventBatch(events=events).model_dump(
                by_alias=True, mode="json"
            ),
        )
        response.raise_for_status()
        accepted = response.json()
        if not isinstance(accepted, list) or len(accepted) != len(events):
            raise RuntimeError("FAIR returned an invalid event batch response")
        return [ExecutionEventRead.model_validate(item) for item in accepted]

    async def emit(
        self,
        event_type: str,
        *,
        payload: dict[str, Any] | None = None,
        schema_uri: str | None = None,
        producer_event_id: str | None = None,
        visibility: str = "user",
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> ExecutionEventRead:
        self._producer_sequence += 1
        event = ExecutionEventCreate(
            producer_source=self._producer_source,
            producer_event_id=producer_event_id or str(uuid4()),
            producer_sequence=self._producer_sequence,
            type=event_type,
            schema_uri=schema_uri or f"urn:fair:event:{event_type}:v1",
            visibility=visibility,
            payload=payload or {},
            trace_id=trace_id,
            span_id=span_id,
        )
        return await self.emit_event(event)

    async def started(self, **payload: Any) -> ExecutionEventRead:
        return await self.emit("execution.started", payload=payload)

    async def waiting(self, reason: str, **payload: Any) -> ExecutionEventRead:
        return await self.emit(
            "execution.waiting", payload={"reason": reason, **payload}
        )

    async def completed(
        self, output_summary: dict[str, Any] | None = None
    ) -> ExecutionEventRead:
        return await self.emit(
            "execution.completed",
            payload={"output_summary": output_summary}
            if output_summary is not None
            else {},
        )

    async def failed(
        self, error: str, *, error_code: str | None = None
    ) -> ExecutionEventRead:
        payload: dict[str, Any] = {"error": error}
        if error_code is not None:
            payload["error_code"] = error_code
        return await self.emit("execution.failed", payload=payload)

    async def message_started(
        self,
        message_id: UUID | str,
        *,
        role: str = "assistant",
        ordinal: int = 1,
    ) -> ExecutionEventRead:
        return await self.emit(
            "message.started",
            payload={
                "message_id": str(message_id),
                "role": role,
                "author_type": "extension",
                "ordinal": ordinal,
            },
        )

    async def message_delta(
        self,
        message_id: UUID | str,
        part_id: UUID | str,
        text: str,
        *,
        ordinal: int = 1,
        part_type: str = "text",
    ) -> ExecutionEventRead:
        return await self.emit(
            "message.delta",
            payload={
                "message_id": str(message_id),
                "part_id": str(part_id),
                "ordinal": ordinal,
                "part_type": part_type,
                "text": text,
            },
        )

    async def message_completed(self, message_id: UUID | str) -> ExecutionEventRead:
        return await self.emit(
            "message.completed", payload={"message_id": str(message_id)}
        )

    async def artifact_created(
        self,
        artifact_id: UUID | str,
        artifact_version_id: UUID | str,
        *,
        kind_uri: str,
        title: str | None = None,
        media_type: str | None = None,
        content_hash: str | None = None,
        size_bytes: int | None = None,
        uri: str | None = None,
    ) -> ExecutionEventRead:
        """Announce a durable ArtifactVersion produced by this Execution."""

        payload: dict[str, Any] = {
            "artifact_id": str(artifact_id),
            "artifact_version_id": str(artifact_version_id),
            "kind_uri": kind_uri,
        }
        optional = {
            "title": title,
            "media_type": media_type,
            "content_hash": content_hash,
            "size_bytes": size_bytes,
            "uri": uri,
        }
        payload.update(
            {key: value for key, value in optional.items() if value is not None}
        )
        return await self.emit("artifact.created", payload=payload)

    async def create_artifact(
        self,
        *,
        title: str,
        kind_uri: str,
        version: dict[str, Any],
        finalize: bool = True,
        client_request_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a provenance-stamped ArtifactVersion for this Execution."""

        await self._ensure_authorization()
        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/artifacts",
            headers=self._authorization_headers,
            json={
                "title": title,
                "kindUri": kind_uri,
                "version": version,
                "finalize": finalize,
                **({"clientRequestId": client_request_id} if client_request_id else {}),
            },
        )
        response.raise_for_status()
        artifact = response.json()
        if not isinstance(artifact, dict):
            raise RuntimeError("FAIR returned an invalid artifact response")
        return artifact

    async def interaction_requested(
        self,
        interaction_id: UUID | str,
        *,
        kind: str,
        schema: dict[str, Any],
        message: str,
        choices: list[dict[str, Any]] | None = None,
        target_url: str | None = None,
        expires_at: datetime | None = None,
    ) -> ExecutionEventRead:
        """Create a durable user interaction request through the event log."""

        payload: dict[str, Any] = {
            "interaction_id": str(interaction_id),
            "kind": kind,
            "schema": schema,
            "message": message,
        }
        if choices is not None:
            payload["choices"] = choices
        if target_url is not None:
            payload["target_url"] = target_url
        if expires_at is not None:
            payload["expires_at"] = expires_at.isoformat()
        return await self.emit("interaction.requested", payload=payload)

    async def invoke_tool(
        self,
        *,
        capability_definition_id: UUID | str,
        input: dict[str, Any],
        idempotency_key: str,
    ) -> ToolInvocationRead:
        """Invoke a platform-linked tool allowed by this capability pin."""

        await self._ensure_authorization()
        request = ToolInvocationRequest(
            capability_definition_id=capability_definition_id,
            input=input,
            idempotency_key=idempotency_key,
        )
        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/tools",
            headers=self._authorization_headers,
            json=request.model_dump(by_alias=True, mode="json"),
        )
        response.raise_for_status()
        return ToolInvocationRead.model_validate(response.json())

    async def read_tool(self, tool_execution_id: UUID | str) -> ToolInvocationRead:
        await self._ensure_authorization()
        response = await self._client.get(
            f"/api/v1/executions/{self.execution_id}/tools/{tool_execution_id}",
            headers=self._authorization_headers,
        )
        response.raise_for_status()
        return ToolInvocationRead.model_validate(response.json())

    async def stream_text(
        self,
        tokens: AsyncIterable[str],
        *,
        message_id: UUID | str,
        part_id: UUID | str,
        flush_interval: float = 0.1,
        max_chars: int = 2048,
    ) -> None:
        """Stream token output as bounded durable chunks, not one request per token."""

        if flush_interval <= 0 or max_chars < 1:
            raise ValueError("flush_interval and max_chars must be positive")
        await self.message_started(message_id)
        buffer: list[str] = []
        buffer_size = 0
        last_flush = asyncio.get_running_loop().time()
        async for token in tokens:
            if not token:
                continue
            buffer.append(token)
            buffer_size += len(token)
            now = asyncio.get_running_loop().time()
            if buffer_size >= max_chars or now - last_flush >= flush_interval:
                await self.message_delta(message_id, part_id, "".join(buffer))
                buffer.clear()
                buffer_size = 0
                last_flush = now
        if buffer:
            await self.message_delta(message_id, part_id, "".join(buffer))
        await self.message_completed(message_id)


__all__ = ["ExecutionReporter"]

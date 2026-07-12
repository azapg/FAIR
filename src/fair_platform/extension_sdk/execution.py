from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx

from fair_platform.extension_sdk.auth import ExtensionCredentials
from fair_platform.extension_sdk.client import build_platform_client
from fair_platform.extension_sdk.contracts.events import (
    ExecutionEventBatch,
    ExecutionEventCreate,
    ExecutionEventRead,
)


class ExecutionReporter:
    """Small framework-agnostic reporter for FAIR Execution events."""

    def __init__(
        self,
        *,
        execution_id: UUID | str,
        platform_url: str,
        credentials: ExtensionCredentials,
        timeout: float = 20.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.execution_id = str(execution_id)
        self._credentials = credentials
        self._client = client or build_platform_client(
            platform_url=platform_url,
            credentials=credentials,
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

    async def emit_event(self, event: ExecutionEventCreate) -> ExecutionEventRead:
        """Send one already-built event, preserving its retry identity."""

        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/events/ingest",
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
        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/events/ingest",
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
            producer_source=self._credentials.extension_id,
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

    async def completed(self, output_summary: dict[str, Any] | None = None) -> ExecutionEventRead:
        return await self.emit(
            "execution.completed",
            payload={"output_summary": output_summary} if output_summary is not None else {},
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
        payload.update({key: value for key, value in optional.items() if value is not None})
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

        response = await self._client.post(
            f"/api/v1/executions/{self.execution_id}/artifacts",
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

__all__ = ["ExecutionReporter"]

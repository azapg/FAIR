from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx
from sqlalchemy.orm import Session

from fair_platform.backend.services.execution_outbox import (
    claim_dispatch,
    mark_dispatch_failed,
    mark_dispatched,
)
from fair_platform.backend.data.models import (
    Execution,
    ExecutionDispatchOutbox,
    ExtensionInstallation,
    ExtensionInstallationStatus,
)


@dataclass(frozen=True)
class ExecutionDispatchResult:
    dispatch_id: str
    idempotency_key: str
    delivered: bool
    status_code: int | None = None
    error: str | None = None


class ExecutionOutboxDispatcher:
    """Lease durable commands and deliver them directly to an Extension."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        http_client: httpx.AsyncClient | None = None,
        worker_id: str = "execution-outbox-worker",
        lease_seconds: int = 30,
        poll_interval_s: float = 0.5,
        request_timeout_s: float = 20.0,
        max_attempts: int = 5,
    ):
        self._session_factory = session_factory
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._poll_interval_s = poll_interval_s
        self._max_attempts = max_attempts
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=request_timeout_s)
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._owns_http_client:
            await self._http.aclose()

    async def run(self) -> None:
        while self._running:
            result = await self.run_once()
            if result is None:
                await asyncio.sleep(self._poll_interval_s)

    async def run_once(self) -> ExecutionDispatchResult | None:
        with self._session_factory() as session:
            dispatch = claim_dispatch(
                session,
                worker_id=self._worker_id,
                lease_seconds=self._lease_seconds,
            )
            if dispatch is None:
                session.rollback()
                return None

            execution = session.get(Execution, dispatch.execution_id)
            installation = (
                session.get(ExtensionInstallation, execution.extension_installation_id)
                if execution is not None
                else None
            )
            dispatch_id = str(dispatch.id)
            dispatch_uuid = dispatch.id
            idempotency_key = dispatch.job_id
            attempt_count = dispatch.attempt_count
            command_kind = getattr(
                dispatch.command_kind, "value", dispatch.command_kind
            )
            if (
                execution is None
                or installation is None
                or getattr(installation.status, "value", installation.status)
                != ExtensionInstallationStatus.enabled.value
                or not installation.dispatch_url
            ):
                reason = "Execution has no enabled Extension dispatch target"
                mark_dispatch_failed(
                    session,
                    dispatch.id,
                    error=reason,
                    dead_letter=True,
                )
                session.commit()
                return ExecutionDispatchResult(
                    dispatch_id=dispatch_id,
                    idempotency_key=idempotency_key,
                    delivered=False,
                    error=reason,
                )
            dispatch_url = installation.dispatch_url
            body = {
                "commandId": dispatch_id,
                "idempotencyKey": idempotency_key,
                "command": command_kind,
                "execution": {
                    "id": str(execution.id),
                    "rootExecutionId": str(execution.root_execution_id),
                    "capabilityId": execution.capability_id,
                    "capabilityVersion": execution.capability_version,
                    "deadlineAt": execution.deadline_at.isoformat()
                    if execution.deadline_at
                    else None,
                },
                "payload": dict(dispatch.payload or {}),
            }
            session.commit()

        try:
            response = await self._http.post(
                dispatch_url,
                json=body,
                headers={
                    "X-FAIR-Dispatch-Id": dispatch_id,
                    "Idempotency-Key": idempotency_key,
                },
            )
            response.raise_for_status()
        except Exception as exc:
            retry_delay = min(2 ** max(attempt_count - 1, 0), 60)
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
            dead_letter = attempt_count >= self._max_attempts
            with self._session_factory() as session:
                failed = session.get(ExecutionDispatchOutbox, dispatch_uuid)
                if failed is not None:
                    mark_dispatch_failed(
                        session,
                        failed.id,
                        error=str(exc),
                        retry_at=None if dead_letter else retry_at,
                        dead_letter=dead_letter,
                    )
                    session.commit()
            return ExecutionDispatchResult(
                dispatch_id=dispatch_id,
                idempotency_key=idempotency_key,
                delivered=False,
                error=str(exc),
            )

        with self._session_factory() as session:
            current = session.get(ExecutionDispatchOutbox, dispatch_uuid)
            if current is not None:
                mark_dispatched(session, current.id)
                session.commit()
        return ExecutionDispatchResult(
            dispatch_id=dispatch_id,
            idempotency_key=idempotency_key,
            delivered=True,
            status_code=response.status_code,
        )


__all__ = ["ExecutionDispatchResult", "ExecutionOutboxDispatcher"]

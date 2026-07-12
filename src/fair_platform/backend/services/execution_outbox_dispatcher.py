from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from fair_platform.backend.services.execution_outbox import (
    claim_dispatch,
    mark_dispatch_failed,
    mark_dispatched,
)
from fair_platform.backend.data.models.execution import ExecutionDispatchOutbox
from fair_platform.backend.services.job_queue import JobMessage, JobQueue


@dataclass(frozen=True)
class ExecutionDispatchResult:
    dispatch_id: str
    job_id: str
    queued: bool
    error: str | None = None


class ExecutionOutboxDispatcher:
    """Bridge durable Execution dispatches into the existing JobQueue.

    Claiming and leasing happen in the database. Queue delivery is deliberately
    a separate step: if the worker dies between the two, the lease expires and
    the same stable job ID is delivered again.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        queue: JobQueue,
        worker_id: str = "execution-outbox-worker",
        lease_seconds: int = 30,
        poll_interval_s: float = 0.5,
    ):
        self._session_factory = session_factory
        self._queue = queue
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._poll_interval_s = poll_interval_s
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

            job = JobMessage(
                job_id=dispatch.job_id,
                target=dispatch.target,
                payload=dict(dispatch.payload or {}),
                metadata={
                    "execution_id": str(dispatch.execution_id),
                    "dispatch_id": str(dispatch.id),
                    "command_kind": getattr(dispatch.command_kind, "value", dispatch.command_kind),
                },
            )
            dispatch_id = str(dispatch.id)
            job_id = dispatch.job_id
            session.commit()

        try:
            await self._queue.enqueue(job)
        except Exception as exc:
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=1)
            with self._session_factory() as session:
                failed = session.get(ExecutionDispatchOutbox, dispatch.id)
                if failed is not None:
                    mark_dispatch_failed(
                        session,
                        failed.id,
                        error=str(exc),
                        retry_at=retry_at,
                    )
                    session.commit()
            return ExecutionDispatchResult(
                dispatch_id=dispatch_id,
                job_id=job_id,
                queued=False,
                error=str(exc),
            )

        with self._session_factory() as session:
            current = session.get(ExecutionDispatchOutbox, dispatch.id)
            if current is not None:
                mark_dispatched(session, current.id)
                session.commit()
        return ExecutionDispatchResult(
            dispatch_id=dispatch_id,
            job_id=job_id,
            queued=True,
        )


__all__ = ["ExecutionDispatchResult", "ExecutionOutboxDispatcher"]

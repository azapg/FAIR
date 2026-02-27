from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from fair_platform.backend.services.extension_registry import LocalExtensionRegistry
from fair_platform.backend.services.job_queue import JobMessage, JobQueue, JobStatus


@dataclass
class DispatchResult:
    job_id: str
    ok: bool
    status_code: int | None = None
    error: str | None = None


class JobDispatcher:
    """Pull jobs from the queue and forward them to registered extensions."""

    def __init__(
        self,
        queue: JobQueue,
        registry: LocalExtensionRegistry,
        http_client: httpx.AsyncClient | None = None,
        *,
        request_timeout_s: float = 20.0,
        dequeue_timeout_s: float = 1.0,
        max_retries: int = 2,
    ):
        self._queue = queue
        self._registry = registry
        self._request_timeout_s = request_timeout_s
        self._dequeue_timeout_s = dequeue_timeout_s
        self._max_retries = max_retries
        self._owns_client = http_client is None
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
        if self._owns_client:
            await self._http.aclose()

    async def run(self) -> None:
        while self._running:
            await self.run_once(timeout=self._dequeue_timeout_s)

    async def run_once(self, timeout: float | None = None) -> DispatchResult | None:
        job = await self._queue.dequeue(timeout=timeout)
        if job is None:
            return None
        return await self._dispatch_job(job)

    async def _dispatch_job(self, job: JobMessage) -> DispatchResult:
        try:
            attempts = int(job.metadata.get("_dispatch_attempt", 0))
        except (ValueError, TypeError):
            attempts = 0
        await self._queue.set_state(
            job.job_id,
            JobStatus.DISPATCHED,
            details={"attempt": attempts + 1},
        )

        extension = await self._registry.get(job.target)
        if extension is None:
            return await self._fail_job(
                job,
                error=f"Extension {job.target!r} is not registered or is disabled",
                code="extension_not_found",
            )

        body = {
            "job_id": job.job_id,
            "target": job.target,
            "payload": job.payload,
            "metadata": job.metadata,
        }

        try:
            response = await self._http.post(extension.webhook_url, json=body)
            response.raise_for_status()
        except Exception as exc:
            if attempts < self._max_retries:
                retry_job = JobMessage(
                    job_id=job.job_id,
                    target=job.target,
                    payload=job.payload,
                    created_at=job.created_at,
                    metadata={**job.metadata, "_dispatch_attempt": attempts + 1},
                )
                await self._queue.enqueue(retry_job)
                await self._queue.set_state(
                    job.job_id,
                    JobStatus.QUEUED,
                    details={"retrying": True, "attempt": attempts + 1},
                )
                return DispatchResult(
                    job_id=job.job_id,
                    ok=False,
                    error=str(exc),
                )
            return await self._fail_job(
                job,
                error=str(exc),
                code="dispatch_error",
            )

        await self._queue.set_state(
            job.job_id,
            JobStatus.RUNNING,
            details={"dispatch_status": response.status_code},
        )
        return DispatchResult(
            job_id=job.job_id,
            ok=True,
            status_code=response.status_code,
        )

    async def _fail_job(self, job: JobMessage, error: str, code: str) -> DispatchResult:
        await self._queue.set_state(
            job.job_id,
            JobStatus.FAILED,
            details={"error": error, "code": code},
        )
        return DispatchResult(
            job_id=job.job_id,
            ok=False,
            error=error,
        )


__all__ = ["DispatchResult", "JobDispatcher"]

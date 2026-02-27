from __future__ import annotations

import asyncio
import importlib
import json
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from dotenv import load_dotenv

load_dotenv()

"""Job queue primitives for the API control-plane.

This module provides a backend-agnostic asynchronous interface that supports:
1. Job submission and dispatch (`enqueue` / `dequeue`)
2. Job state tracking (`set_state` / `get_state`)
3. Real-time update streaming (`publish_update` / `subscribe_updates`)

Two implementations are available:
- `LocalJobQueue`: in-process queue (`asyncio.Queue`) for local development/tests.
- `RedisJobQueue`: cross-process queue + pub/sub for production scale.

Quick example (producer + dispatcher):

```python
from fair_platform.backend.services.job_queue import (
    JobMessage,
    JobStatus,
    JobUpdate,
    create_job_queue,
)

queue = await create_job_queue()

# Producer/API route
job = JobMessage(job_id="job_123", target="fairgrade.core", payload={"submission_id": "s1"})
await queue.enqueue(job)

# Dispatcher worker
next_job = await queue.dequeue(timeout=1.0)
if next_job:
    await queue.set_state(next_job.job_id, JobStatus.RUNNING)
    await queue.publish_update(
        JobUpdate(job_id=next_job.job_id, event="progress", payload={"percent": 20})
    )
```

Quick example (SSE-like consumer):

```python
subscription = await queue.subscribe_updates("job_123")
async with subscription:
    update = await subscription.get(timeout=5.0)
    if update:
        print(update.event, update.payload)
```
"""


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp in ISO format."""
    return datetime.now(tz=timezone.utc).isoformat()


class JobStatus(StrEnum):
    """Canonical lifecycle states for a job.

    These values are intentionally transport-friendly strings so they can be
    serialized directly to JSON and consumed by any SDK language.
    """

    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobMessage:
    """A unit of work to be dispatched to an extension/service.

    Attributes:
        job_id: Stable id shared across API, dispatcher, and client.
        target: Extension identifier or routing key.
        payload: Extension-specific request data.
        created_at: UTC ISO timestamp (set automatically).
        metadata: Optional transport-level metadata (trace ids, actor info).
    """

    job_id: str
    target: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=_utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobState:
    """Persisted status snapshot for a single job."""

    job_id: str
    status: JobStatus
    updated_at: str = field(default_factory=_utc_now_iso)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobUpdate:
    """Incremental event emitted while a job is processed.

    Typical events:
    - `progress`: numeric progress updates
    - `token`: LLM token/text stream chunks
    - `log`: human-readable log lines
    - `result`: final structured output
    """

    job_id: str
    event: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=_utc_now_iso)


class JobUpdateSubscription(ABC):
    """Abstract stream handle for per-job updates.

    Implementations should be safe to consume in an SSE loop.
    `get(timeout=...)` should return `None` on timeout instead of raising.
    """

    @abstractmethod
    async def get(self, timeout: float | None = None) -> JobUpdate | None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> "JobUpdateSubscription":
        return self

    async def __aexit__(self, *_ignored: object) -> None:
        await self.close()


class JobQueue(ABC):
    """Common asynchronous contract for queue backends.

    Design notes:
    - API handlers only need `enqueue`, `get_state`, and `subscribe_updates`.
    - Dispatcher workers use `dequeue`, `set_state`, and `publish_update`.
    - Keeping this interface narrow makes it straightforward to implement in
      other languages/services while preserving behavior.
    """

    @abstractmethod
    async def enqueue(self, job: JobMessage) -> None:
        raise NotImplementedError

    @abstractmethod
    async def dequeue(self, timeout: float | None = None) -> JobMessage | None:
        raise NotImplementedError

    @abstractmethod
    async def set_state(
        self,
        job_id: str,
        status: JobStatus,
        details: dict[str, Any] | None = None,
    ) -> JobState:
        raise NotImplementedError

    @abstractmethod
    async def get_state(self, job_id: str) -> JobState | None:
        raise NotImplementedError

    @abstractmethod
    async def publish_update(self, update: JobUpdate) -> None:
        raise NotImplementedError

    @abstractmethod
    async def subscribe_updates(self, job_id: str) -> JobUpdateSubscription:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


class LocalJobUpdateSubscription(JobUpdateSubscription):
    """In-memory subscription for `LocalJobQueue`."""

    def __init__(
        self,
        job_id: str,
        queue: asyncio.Queue[JobUpdate],
        detach_callback: Any,
    ):
        self._job_id = job_id
        self._queue = queue
        self._detach_callback = detach_callback
        self._closed = False

    async def get(self, timeout: float | None = None) -> JobUpdate | None:
        if self._closed:
            return None
        if timeout is None:
            return await self._queue.get()
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._detach_callback(self._job_id, self._queue)


class LocalJobQueue(JobQueue):
    """Single-process queue backend for local/dev execution.

    This implementation requires no external services and is ideal for:
    - local onboarding
    - unit/integration tests
    - single-worker runs

    It is not suitable for horizontal scaling because data lives in process memory.
    """

    def __init__(self):
        self._jobs: asyncio.Queue[JobMessage] = asyncio.Queue()
        self._states: dict[str, JobState] = {}
        self._subscribers: dict[str, set[asyncio.Queue[JobUpdate]]] = defaultdict(set)

    async def enqueue(self, job: JobMessage) -> None:
        await self._jobs.put(job)
        await self.set_state(job.job_id, JobStatus.QUEUED)

    async def dequeue(self, timeout: float | None = None) -> JobMessage | None:
        if timeout is None:
            return await self._jobs.get()
        try:
            return await asyncio.wait_for(self._jobs.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def set_state(
        self,
        job_id: str,
        status: JobStatus,
        details: dict[str, Any] | None = None,
    ) -> JobState:
        state = JobState(
            job_id=job_id,
            status=status,
            details=details or {},
        )
        self._states[job_id] = state
        return state

    async def get_state(self, job_id: str) -> JobState | None:
        return self._states.get(job_id)

    async def publish_update(self, update: JobUpdate) -> None:
        subscribers = self._subscribers.get(update.job_id, set())
        # Fan-out: every active subscriber for this job receives the same event.
        for queue in subscribers:
            await queue.put(update)

    async def subscribe_updates(self, job_id: str) -> JobUpdateSubscription:
        queue: asyncio.Queue[JobUpdate] = asyncio.Queue()
        self._subscribers[job_id].add(queue)
        return LocalJobUpdateSubscription(job_id, queue, self._detach_subscriber)

    async def close(self) -> None:
        self._states.clear()
        self._subscribers.clear()

    def _detach_subscriber(self, job_id: str, queue: asyncio.Queue[JobUpdate]) -> None:
        subscribers = self._subscribers.get(job_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(job_id, None)


class RedisJobUpdateSubscription(JobUpdateSubscription):
    """Redis Pub/Sub backed subscription for cross-worker update streaming."""

    def __init__(self, pubsub: Any, channel: str):
        self._pubsub = pubsub
        self._channel = channel
        self._closed = False

    async def get(self, timeout: float | None = None) -> JobUpdate | None:
        if self._closed:
            return None
        message = await self._pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=timeout,
        )
        if not message:
            return None
        data = message["data"]
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return JobUpdate(**json.loads(data))

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._pubsub.unsubscribe(self._channel)
        await self._pubsub.close()


class RedisJobQueue(JobQueue):
    """Redis-backed queue for multi-worker deployments.

    Redis data model:
    - Job queue: Redis list (`RPUSH` / `BLPOP`)
    - Job states: Redis keys (`SET` / `GET`)
    - Job updates: Redis Pub/Sub channels

    This enables stateless API workers where any worker can accept update posts
    and any other worker can stream those updates to connected clients.
    """

    def __init__(
        self,
        redis_client: Any,
        queue_name: str = "fair:jobs",
        updates_prefix: str = "fair:job-updates",
        state_prefix: str = "fair:job-states",
    ):
        self._redis = redis_client
        self._queue_name = queue_name
        self._updates_prefix = updates_prefix
        self._state_prefix = state_prefix

    @classmethod
    async def from_url(
        cls,
        redis_url: str,
        queue_name: str = "fair:jobs",
        updates_prefix: str = "fair:job-updates",
        state_prefix: str = "fair:job-states",
    ) -> "RedisJobQueue":
        """Create a queue from a Redis URL.

        Import is lazy so local/dev mode can run without importing `redis` unless
        Redis backend is actually selected.
        """

        redis_module = importlib.import_module("redis.asyncio")
        redis_client = redis_module.from_url(redis_url, decode_responses=False)
        return cls(
            redis_client=redis_client,
            queue_name=queue_name,
            updates_prefix=updates_prefix,
            state_prefix=state_prefix,
        )

    async def enqueue(self, job: JobMessage) -> None:
        await self._redis.rpush(self._queue_name, json.dumps(asdict(job)))
        await self.set_state(job.job_id, JobStatus.QUEUED)

    async def dequeue(self, timeout: float | None = None) -> JobMessage | None:
        # `BLPOP timeout=0` means "block forever" in Redis.
        redis_timeout = 0 if timeout is None else float(timeout)
        response = await self._redis.blpop(self._queue_name, timeout=redis_timeout)
        if response is None:
            return None
        _, raw_payload = response
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")
        return JobMessage(**json.loads(raw_payload))

    async def set_state(
        self,
        job_id: str,
        status: JobStatus,
        details: dict[str, Any] | None = None,
    ) -> JobState:
        state = JobState(
            job_id=job_id,
            status=status,
            details=details or {},
        )
        key = self._state_key(job_id)
        await self._redis.set(key, json.dumps(asdict(state)))
        return state

    async def get_state(self, job_id: str) -> JobState | None:
        key = self._state_key(job_id)
        raw_state = await self._redis.get(key)
        if raw_state is None:
            return None
        if isinstance(raw_state, bytes):
            raw_state = raw_state.decode("utf-8")
        payload = json.loads(raw_state)
        payload["status"] = JobStatus(payload["status"])
        return JobState(**payload)

    async def publish_update(self, update: JobUpdate) -> None:
        channel = self._updates_channel(update.job_id)
        await self._redis.publish(channel, json.dumps(asdict(update)))

    async def subscribe_updates(self, job_id: str) -> JobUpdateSubscription:
        channel = self._updates_channel(job_id)
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        return RedisJobUpdateSubscription(pubsub=pubsub, channel=channel)

    async def close(self) -> None:
        await self._redis.close()

    def _updates_channel(self, job_id: str) -> str:
        return f"{self._updates_prefix}:{job_id}"

    def _state_key(self, job_id: str) -> str:
        return f"{self._state_prefix}:{job_id}"


def get_job_queue_backend() -> str:
    """Return the normalized queue backend name (`local` or `redis`)."""
    return os.getenv("FAIR_JOB_QUEUE_BACKEND", "local").strip().lower()


async def create_job_queue() -> JobQueue:
    """Factory that builds the configured queue backend.

    Environment variables:
    - `FAIR_JOB_QUEUE_BACKEND`: `local` (default) or `redis`
    - `FAIR_REDIS_URL`: Redis connection URL for redis backend
    - `FAIR_JOB_QUEUE_NAME`: list key for pending jobs
    - `FAIR_JOB_UPDATES_PREFIX`: pub/sub channel prefix
    - `FAIR_JOB_STATE_PREFIX`: key prefix for persisted states
    """

    backend = get_job_queue_backend()
    if backend == "local":
        return LocalJobQueue()
    if backend == "redis":
        redis_url = os.getenv("FAIR_REDIS_URL", "redis://127.0.0.1:6379/0")
        queue_name = os.getenv("FAIR_JOB_QUEUE_NAME", "fair:jobs")
        updates_prefix = os.getenv("FAIR_JOB_UPDATES_PREFIX", "fair:job-updates")
        state_prefix = os.getenv("FAIR_JOB_STATE_PREFIX", "fair:job-states")
        return await RedisJobQueue.from_url(
            redis_url=redis_url,
            queue_name=queue_name,
            updates_prefix=updates_prefix,
            state_prefix=state_prefix,
        )
    raise ValueError(
        f"Unsupported FAIR_JOB_QUEUE_BACKEND value: {backend!r}. Expected 'local' or 'redis'."
    )


__all__ = [
    "JobStatus",
    "JobMessage",
    "JobState",
    "JobUpdate",
    "JobUpdateSubscription",
    "JobQueue",
    "LocalJobQueue",
    "RedisJobQueue",
    "get_job_queue_backend",
    "create_job_queue",
]

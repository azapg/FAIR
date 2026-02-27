import json
from dataclasses import asdict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from fair_platform.backend.services.job_queue import (
    JobMessage,
    JobStatus,
    JobUpdate,
    LocalJobQueue,
    RedisJobQueue,
    create_job_queue,
)


@pytest.mark.asyncio
async def test_local_job_queue_enqueue_dequeue_and_state():
    queue = LocalJobQueue()
    job = JobMessage(job_id="job-1", target="fairgrade.core", payload={"x": 1})

    await queue.enqueue(job)
    popped = await queue.dequeue(timeout=0.1)
    state = await queue.get_state("job-1")

    assert popped == job
    assert state is not None
    assert state.job_id == "job-1"
    assert state.status == JobStatus.QUEUED


@pytest.mark.asyncio
async def test_local_job_queue_dequeue_timeout_returns_none():
    queue = LocalJobQueue()
    popped = await queue.dequeue(timeout=0.01)
    assert popped is None


@pytest.mark.asyncio
async def test_local_job_queue_update_fanout_to_multiple_subscribers():
    queue = LocalJobQueue()
    sub1 = await queue.subscribe_updates("job-2")
    sub2 = await queue.subscribe_updates("job-2")
    update = JobUpdate(job_id="job-2", event="progress", payload={"step": 2})

    await queue.publish_update(update)
    u1 = await sub1.get(timeout=0.1)
    u2 = await sub2.get(timeout=0.1)

    assert u1 == update
    assert u2 == update

    await sub1.close()
    await sub2.close()
    await queue.close()


@pytest.mark.asyncio
async def test_redis_job_queue_enqueue_dequeue_and_state():
    redis = AsyncMock()
    queue = RedisJobQueue(redis_client=redis)

    job = JobMessage(job_id="job-3", target="extension", payload={"foo": "bar"})
    await queue.enqueue(job)

    redis.rpush.assert_awaited_once()
    queue_name, payload = redis.rpush.await_args.args
    assert queue_name == "fair:jobs"
    assert json.loads(payload)["job_id"] == "job-3"
    redis.set.assert_awaited_once()

    redis.blpop.return_value = ("fair:jobs", json.dumps(asdict(job)).encode("utf-8"))
    popped = await queue.dequeue(timeout=2.4)
    assert popped is not None
    assert popped.job_id == "job-3"
    assert redis.blpop.await_args.kwargs == {"timeout": 2}

    redis.get.return_value = json.dumps(
        {
            "job_id": "job-3",
            "status": "running",
            "updated_at": "2026-02-27T00:00:00+00:00",
            "details": {"attempt": 1},
        }
    ).encode("utf-8")
    state = await queue.get_state("job-3")
    assert state is not None
    assert state.status == JobStatus.RUNNING


@pytest.mark.asyncio
async def test_redis_job_queue_update_pubsub():
    redis = AsyncMock()
    pubsub = AsyncMock()
    pubsub.get_message.return_value = {
        "type": "message",
        "channel": b"fair:job-updates:job-4",
        "data": json.dumps(
            {
                "job_id": "job-4",
                "event": "token",
                "payload": {"chunk": "abc"},
                "created_at": "2026-02-27T00:00:00+00:00",
            }
        ).encode("utf-8"),
    }
    redis.pubsub = Mock(return_value=pubsub)
    queue = RedisJobQueue(redis_client=redis)

    update = JobUpdate(job_id="job-4", event="token", payload={"chunk": "abc"})
    await queue.publish_update(update)
    redis.publish.assert_awaited_once()

    sub = await queue.subscribe_updates("job-4")
    item = await sub.get(timeout=1.0)
    assert item is not None
    assert item.job_id == "job-4"
    assert item.event == "token"
    assert item.payload == {"chunk": "abc"}

    await sub.close()
    pubsub.unsubscribe.assert_awaited_once_with("fair:job-updates:job-4")
    pubsub.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_job_queue_factory_local_and_redis():
    with patch.dict("os.environ", {"FAIR_JOB_QUEUE_BACKEND": "local"}, clear=False):
        queue = await create_job_queue()
        assert isinstance(queue, LocalJobQueue)

    with patch.dict(
        "os.environ",
        {
            "FAIR_JOB_QUEUE_BACKEND": "redis",
            "FAIR_REDIS_URL": "redis://localhost:6379/1",
        },
        clear=False,
    ):
        sentinel_queue = object()
        with patch(
            "fair_platform.backend.services.job_queue.RedisJobQueue.from_url",
            AsyncMock(return_value=sentinel_queue),
        ) as from_url:
            queue = await create_job_queue()
            assert queue is sentinel_queue
            from_url.assert_awaited_once()

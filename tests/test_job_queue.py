from unittest.mock import patch

import pytest

from fair_platform.backend.services.job_queue import (
    JobMessage,
    JobStatus,
    JobUpdate,
    LocalJobQueue,
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
async def test_create_job_queue_factory_local():
    with patch.dict("os.environ", {"FAIR_JOB_QUEUE_BACKEND": "local"}, clear=False):
        queue = await create_job_queue()
        assert isinstance(queue, LocalJobQueue)

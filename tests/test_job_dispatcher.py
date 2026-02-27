from unittest.mock import AsyncMock, Mock

import pytest

from fair_platform.backend.services.extension_registry import (
    ExtensionRegistration,
    LocalExtensionRegistry,
)
from fair_platform.backend.services.job_dispatcher import JobDispatcher
from fair_platform.backend.services.job_queue import JobMessage, JobStatus, LocalJobQueue


@pytest.mark.asyncio
async def test_dispatcher_sends_job_to_registered_extension_and_sets_running():
    queue = LocalJobQueue()
    registry = LocalExtensionRegistry()
    await registry.register(
        ExtensionRegistration(
            extension_id="fairgrade.core",
            webhook_url="http://extension/jobs",
        )
    )

    http_client = AsyncMock()
    response = Mock()
    response.status_code = 202
    response.raise_for_status = Mock(return_value=None)
    http_client.post.return_value = response

    dispatcher = JobDispatcher(queue=queue, registry=registry, http_client=http_client)
    await queue.enqueue(JobMessage(job_id="job-d-1", target="fairgrade.core", payload={"a": 1}))

    result = await dispatcher.run_once(timeout=0.1)
    state = await queue.get_state("job-d-1")

    assert result is not None
    assert result.ok is True
    assert state is not None
    assert state.status == JobStatus.RUNNING
    http_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatcher_fails_job_when_extension_not_found():
    queue = LocalJobQueue()
    registry = LocalExtensionRegistry()
    dispatcher = JobDispatcher(queue=queue, registry=registry, http_client=AsyncMock())

    await queue.enqueue(JobMessage(job_id="job-d-2", target="missing.extension", payload={}))
    result = await dispatcher.run_once(timeout=0.1)
    state = await queue.get_state("job-d-2")

    assert result is not None
    assert result.ok is False
    assert state is not None
    assert state.status == JobStatus.FAILED
    assert state.details["code"] == "extension_not_found"


@pytest.mark.asyncio
async def test_dispatcher_retries_then_fails():
    queue = LocalJobQueue()
    registry = LocalExtensionRegistry()
    await registry.register(
        ExtensionRegistration(
            extension_id="fairgrade.core",
            webhook_url="http://extension/jobs",
        )
    )

    http_client = AsyncMock()
    http_client.post.side_effect = RuntimeError("network error")

    dispatcher = JobDispatcher(
        queue=queue,
        registry=registry,
        http_client=http_client,
        max_retries=1,
    )
    await queue.enqueue(JobMessage(job_id="job-d-3", target="fairgrade.core", payload={"x": 1}))

    first = await dispatcher.run_once(timeout=0.1)
    state_after_first = await queue.get_state("job-d-3")
    assert first is not None
    assert first.ok is False
    assert state_after_first is not None
    assert state_after_first.status == JobStatus.QUEUED
    assert state_after_first.details["retrying"] is True

    second = await dispatcher.run_once(timeout=0.1)
    state_after_second = await queue.get_state("job-d-3")
    assert second is not None
    assert second.ok is False
    assert state_after_second is not None
    assert state_after_second.status == JobStatus.FAILED
    assert state_after_second.details["code"] == "dispatch_error"

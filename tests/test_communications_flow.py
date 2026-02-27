import asyncio

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fair_platform.backend.main import app
from fair_platform.backend.services.job_dispatcher import JobDispatcher


def test_platform_jobs_api_dispatcher_and_extension_webhook_flow(test_client):
    received: list[dict] = []
    extension_app = FastAPI()

    @extension_app.post("/hooks/jobs")
    async def receive_job(payload: dict):
        received.append(payload)
        return {"accepted": True}

    register_response = test_client.post(
        "/api/extensions/",
        json={
            "extensionId": "mock.echo",
            "webhookUrl": "http://mock-extension/hooks/jobs",
            "intents": ["jobs.test"],
            "capabilities": ["mock"],
        },
    )
    assert register_response.status_code == 201

    create_response = test_client.post(
        "/api/jobs/",
        json={
            "jobId": "job-flow-1",
            "target": "mock.echo",
            "payload": {"text": "hello flow"},
            "metadata": {"source": "integration-test"},
        },
    )
    assert create_response.status_code == 202

    async def _run_dispatch_once():
        async with AsyncClient(
            transport=ASGITransport(app=extension_app),
            base_url="http://mock-extension",
        ) as extension_http_client:
            dispatcher = JobDispatcher(
                queue=app.state.job_queue,
                registry=app.state.extension_registry,
                http_client=extension_http_client,
                max_retries=0,
            )
            result = await dispatcher.run_once(timeout=0.1)
            assert result is not None
            assert result.ok is True
            assert result.status_code == 200

    asyncio.run(_run_dispatch_once())

    assert len(received) == 1
    assert received[0]["job_id"] == "job-flow-1"
    assert received[0]["target"] == "mock.echo"
    assert received[0]["payload"] == {"text": "hello flow"}

    state_response = test_client.get("/api/jobs/job-flow-1")
    assert state_response.status_code == 200
    assert state_response.json()["status"] == "running"

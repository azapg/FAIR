import asyncio
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fair_platform.backend.main import app
from fair_platform.backend.services.job_dispatcher import JobDispatcher
from tests.conftest import extension_auth_headers, get_auth_token


def test_platform_jobs_api_dispatcher_and_extension_webhook_flow(test_client, extension_client_credentials, student_user):
    received: list[dict] = []
    job_id = f"job-flow-{uuid4()}"
    extension_app = FastAPI()

    @extension_app.post("/hooks/jobs")
    async def receive_job(payload: dict):
        received.append(payload)
        return {"accepted": True}

    register_response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://mock-extension/hooks/jobs",
            "intents": ["jobs.test"],
            "capabilities": ["mock"],
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert register_response.status_code == 201
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}

    create_response = test_client.post(
        "/api/jobs/",
        json={
            "jobId": job_id,
            "target": extension_client_credentials["extension_id"],
            "payload": {"action": "echo.text", "params": {"text": "hello flow"}},
            "metadata": {"source": "integration-test"},
        },
        headers=user_headers,
    )
    assert create_response.status_code == 202

    async def _run_dispatch_until_target():
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
            for _ in range(10):
                result = await dispatcher.run_once(timeout=0.1)
                assert result is not None
                if any(item.get("job_id") == job_id for item in received):
                    return
            raise AssertionError("dispatcher did not deliver target job within retry budget")

    asyncio.run(_run_dispatch_until_target())

    assert len(received) >= 1
    matched = next((item for item in received if item.get("job_id") == job_id), None)
    assert matched is not None
    assert matched["target"] == extension_client_credentials["extension_id"]
    assert matched["payload"] == {"action": "echo.text", "params": {"text": "hello flow"}}

    state_response = test_client.get(f"/api/jobs/{job_id}", headers=user_headers)
    assert state_response.status_code == 200
    assert state_response.json()["status"] == "running"

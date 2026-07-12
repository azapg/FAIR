import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.routers.executions import get_stream_session_factory
from fair_platform.backend.data.models import ExtensionClient, Message, User, UserRole
from fair_platform.backend.main import app
from fair_platform.backend.services.execution_outbox_dispatcher import (
    ExecutionOutboxDispatcher,
)
from fair_platform.backend.services.execution_projection import (
    rebuild_execution_projection,
)
from fair_platform.backend.services.extension_auth import hash_extension_secret
from fair_platform.backend.services.extension_registry import (
    ExtensionRegistration,
    LocalExtensionRegistry,
)
from fair_platform.backend.services.job_dispatcher import JobDispatcher
from fair_platform.backend.services.job_queue import LocalJobQueue
from fair_platform.extension_sdk.auth import (
    ExtensionCredentials,
    build_extension_auth_headers,
)
from fair_platform.extension_sdk.execution import ExecutionReporter


def test_mock_extension_outbox_replay_rebuild_and_sse_reconnect(test_db):
    user = User(
        id=uuid4(),
        name="E2E user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    now = datetime.now(timezone.utc)
    with test_db() as session:
        session.add_all(
            [
                user,
                ExtensionClient(
                    extension_id="mock.extension",
                    secret_hash=hash_extension_secret("e2e-secret"),
                    scopes=["executions:events"],
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_stream_session_factory] = lambda: test_db
    client = TestClient(app)
    try:
        thread_response = client.post(
            "/api/v1/threads", json={"title": "E2E thread"}
        )
        assert thread_response.status_code == 201, thread_response.text
        thread_id = thread_response.json()["id"]
        turn_response = client.post(
            f"/api/v1/threads/{thread_id}/turns",
            json={
                "content": "Answer this through the extension",
                "clientRequestId": "e2e-request-1",
                "target": "mock.extension",
            },
        )
        assert turn_response.status_code == 202, turn_response.text
        execution_id = turn_response.json()["executionId"]

        async def run_dispatch() -> None:
            credentials = ExtensionCredentials(
                extension_id="mock.extension",
                extension_secret="e2e-secret",
            )

            async def extension_webhook(request: httpx.Request) -> httpx.Response:
                body = json.loads(request.content)
                dispatched_execution_id = body["payload"]["execution_id"]
                api_client = httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://fair.test",
                    headers=build_extension_auth_headers(credentials),
                )
                reporter = ExecutionReporter(
                    execution_id=dispatched_execution_id,
                    platform_url="http://fair.test",
                    credentials=credentials,
                    client=api_client,
                )
                message_id = uuid4()
                part_id = uuid4()
                await reporter.started()
                await reporter.message_started(message_id)
                await reporter.message_delta(message_id, part_id, "Hello from E2E")
                await reporter.message_completed(message_id)
                await reporter.completed({"answer": "ok"})
                await api_client.aclose()
                return httpx.Response(202, json={"accepted": True})

            queue = LocalJobQueue()
            outbox = ExecutionOutboxDispatcher(
                session_factory=test_db,
                queue=queue,
                worker_id="e2e-outbox-worker",
            )
            outbox_result = await outbox.run_once()
            assert outbox_result is not None
            assert outbox_result.queued is True

            registry = LocalExtensionRegistry()
            await registry.register(
                ExtensionRegistration(
                    extension_id="mock.extension",
                    webhook_url="https://mock.extension/hooks/execution",
                )
            )
            dispatch_http = httpx.AsyncClient(
                transport=httpx.MockTransport(extension_webhook),
                base_url="https://platform.test",
            )
            job_dispatcher = JobDispatcher(
                queue=queue,
                registry=registry,
                http_client=dispatch_http,
            )
            result = await job_dispatcher.run_once(timeout=0.1)
            assert result is not None
            assert result.ok is True
            await dispatch_http.aclose()
            await queue.close()

        asyncio.run(run_dispatch())

        with test_db() as session:
            from fair_platform.backend.data.models import Execution, ExecutionEvent

            execution = session.get(Execution, UUID(execution_id))
            assert execution is not None
            events = list(
                session.query(ExecutionEvent)
                .filter(ExecutionEvent.execution_id == execution.id)
                .order_by(ExecutionEvent.sequence)
            )
            assert [event.type for event in events] == [
                "execution.created",
                "execution.started",
                "message.started",
                "message.delta",
                "message.completed",
                "execution.completed",
            ]

            snapshot = rebuild_execution_projection(session, execution.id)
            session.commit()
            message = (
                session.query(Message)
                .filter(Message.producing_execution_id == execution.id)
                .one()
            )
            assert snapshot is not None
            assert snapshot.last_sequence == 6
            assert message.parts[0].text_content == "Hello from E2E"

        with client.stream(
            "GET",
            f"/api/v1/executions/{execution_id}/stream",
            headers={"Last-Event-ID": "2"},
        ) as response:
            assert response.status_code == 200
            stream_body = response.read().decode("utf-8")
        ids = [
            int(line.removeprefix("id: "))
            for line in stream_body.splitlines()
            if line.startswith("id: ")
        ]
        assert ids == [3, 4, 5, 6]

        with client.stream(
            "GET",
            f"/api/v1/executions/{execution_id}/stream",
            headers={"Last-Event-ID": "4"},
        ) as response:
            assert response.status_code == 200
            reconnect_body = response.read().decode("utf-8")
        reconnect_ids = [
            int(line.removeprefix("id: "))
            for line in reconnect_body.splitlines()
            if line.startswith("id: ")
        ]
        assert reconnect_ids == [5, 6]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_stream_session_factory, None)

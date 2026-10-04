import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.routers.executions import get_stream_session_factory
from fair_platform.backend.data.models import (
    ExtensionInstallation,
    Message,
    User,
    UserRole,
)
from fair_platform.backend.main import app
from fair_platform.backend.services.execution_outbox_dispatcher import (
    ExecutionOutboxDispatcher,
)
from fair_platform.backend.services.execution_projection import (
    rebuild_execution_projection,
)
from fair_platform.backend.services.dispatch_signing import get_dispatch_signer
from fair_platform.extension_sdk.contracts.protocol import ExecutionCommand
from fair_platform.extension_sdk.execution import ExecutionReporter
from fair_platform.extension_sdk.signatures import verify_request_signature
from tests.execution_protocol_helpers import add_agent_capability


def test_mock_extension_outbox_replay_rebuild_and_sse_reconnect(test_db):
    user = User(
        id=uuid4(),
        name="E2E user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    now = datetime.now(timezone.utc)
    with test_db() as session:
        session.add(user)
        capability = add_agent_capability(
            session,
            ExtensionInstallation(
                extension_id="mock.extension",
                dispatch_url="https://mock.extension/hooks/execution",
            ),
        )
        session.commit()
        capability_definition_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_stream_session_factory] = lambda: test_db
    client = TestClient(app)
    try:
        thread_response = client.post("/api/v1/threads", json={"title": "E2E thread"})
        assert thread_response.status_code == 201, thread_response.text
        thread_id = thread_response.json()["id"]
        turn_response = client.post(
            f"/api/v1/threads/{thread_id}/turns",
            json={
                "content": "Answer this through the extension",
                "clientRequestId": "e2e-request-1",
                "capabilityDefinitionId": str(capability_definition_id),
            },
        )
        assert turn_response.status_code == 202, turn_response.text
        execution_id = turn_response.json()["executionId"]

        async def run_dispatch() -> None:
            async def extension_webhook(request: httpx.Request) -> httpx.Response:
                signer = get_dispatch_signer()
                verify_request_signature(
                    method=request.method,
                    target_uri=str(request.url),
                    headers=request.headers,
                    body=request.content,
                    resolve_key=lambda key_id: (
                        signer.public_key
                        if key_id == signer.key_id
                        else (_ for _ in ()).throw(KeyError(key_id))
                    ),
                )
                command = ExecutionCommand.model_validate_json(request.content)
                api_client = httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://fair.test",
                )
                reporter = ExecutionReporter(
                    command=command,
                    client=api_client,
                )
                message_id = uuid4()
                part_id = uuid4()
                await reporter.started()
                await reporter.message_started(message_id)
                await reporter.message_delta(message_id, part_id, "Hello from E2E")
                await reporter.message_completed(message_id)
                await reporter.emit(
                    "extension.diagnostic",
                    visibility="private",
                    payload={"secret": "not user-visible"},
                )
                await reporter.completed({"answer": "ok"})
                await api_client.aclose()
                return httpx.Response(202, json={"accepted": True})

            dispatch_http = httpx.AsyncClient(
                transport=httpx.MockTransport(extension_webhook),
                base_url="https://platform.test",
            )
            outbox = ExecutionOutboxDispatcher(
                session_factory=test_db,
                http_client=dispatch_http,
                worker_id="e2e-outbox-worker",
            )
            result = await outbox.run_once()
            assert result is not None
            assert result.delivered is True
            await dispatch_http.aclose()

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
                "extension.diagnostic",
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
            assert snapshot.last_sequence == 7
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
        assert ids == [3, 4, 5, 7]

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
        assert reconnect_ids == [5, 7]

        # A terminal stream must drain every durable event, even when reconnecting
        # behind more than one server-side replay page.
        with test_db() as session:
            from fair_platform.backend.data.models import ExecutionEvent

            session.add_all(
                [
                    ExecutionEvent(
                        execution_id=UUID(execution_id),
                        sequence=sequence,
                        producer_source="mock.extension",
                        producer_event_id=f"backlog-{sequence}",
                        type="agent.token.chunk",
                        schema_uri="urn:fair:event:agent.token.chunk:v1",
                        occurred_at=now,
                        received_at=now,
                        visibility="user",
                        durability="durable",
                        payload={"text": "x"},
                    )
                    for sequence in range(8, 509)
                ]
            )
            session.commit()
        with client.stream(
            "GET",
            f"/api/v1/executions/{execution_id}/stream",
            headers={"Last-Event-ID": "7"},
        ) as response:
            assert response.status_code == 200
            backlog_body = response.read().decode("utf-8")
        backlog_ids = [
            int(line.removeprefix("id: "))
            for line in backlog_body.splitlines()
            if line.startswith("id: ")
        ]
        assert backlog_ids == list(range(8, 509))
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_stream_session_factory, None)

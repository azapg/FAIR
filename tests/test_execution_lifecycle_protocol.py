from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    Execution,
    ExecutionDispatchOutbox,
    ExecutionEvent,
    ExtensionInstallation,
    User,
)
from fair_platform.backend.main import app
from fair_platform.backend.services.execution_lifecycle import expire_due_executions
from tests.execution_protocol_helpers import (
    add_agent_capability,
    execution_headers,
)


def _user() -> User:
    return User(id=uuid4(), name="Lifecycle User", email=f"{uuid4()}@test", role="user")


def test_user_cancellation_dispatches_once_and_only_accepts_terminal_result(test_db):
    user = _user()
    with test_db() as db:
        db.add(user)
        capability = add_agent_capability(
            db,
            ExtensionInstallation(
                extension_id="cancellable.agent",
                delivery_mode="runner",
            ),
            supports_cancellation=True,
        )
        db.commit()
        capability_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    thread = client.post("/api/v1/threads", json={"title": "Cancel"}).json()
    turn = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={
            "content": "Long task",
            "capabilityDefinitionId": str(capability_id),
        },
    ).json()
    execution_id = turn["executionId"]

    first = client.post(f"/api/v1/executions/{execution_id}/cancel")
    second = client.post(f"/api/v1/executions/{execution_id}/cancel")
    assert first.status_code == second.status_code == 202
    with test_db() as db:
        cancel_dispatches = list(
            db.query(ExecutionDispatchOutbox).filter(
                ExecutionDispatchOutbox.execution_id == UUID(execution_id),
                ExecutionDispatchOutbox.command_kind == "cancel",
            )
        )
        assert len(cancel_dispatches) == 1

    rejected = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=execution_headers(test_db, execution_id),
        json={
            "events": [
                {
                    "producerSource": "cancellable.agent",
                    "producerEventId": "late-completion",
                    "type": "execution.completed",
                    "schemaUri": "urn:fair:event:execution.completed:v1",
                    "payload": {},
                }
            ]
        },
    )
    assert rejected.status_code == 409
    cancelled = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=execution_headers(test_db, execution_id),
        json={
            "events": [
                {
                    "producerSource": "cancellable.agent",
                    "producerEventId": "cancelled",
                    "type": "execution.cancelled",
                    "schemaUri": "urn:fair:event:execution.cancelled:v1",
                    "payload": {"reason": "user_requested"},
                }
            ]
        },
    )
    assert cancelled.status_code == 202, cancelled.text
    assert (
        client.get(f"/api/v1/executions/{execution_id}").json()["status"] == "cancelled"
    )


def test_deadline_watchdog_terminates_once_and_revokes_authority(test_db):
    user = _user()
    with test_db() as db:
        db.add(user)
        capability = add_agent_capability(
            db, ExtensionInstallation(extension_id="deadline.agent")
        )
        execution_id = uuid4()
        execution = Execution(
            id=execution_id,
            root_execution_id=execution_id,
            attempt=1,
            kind="agent",
            capability_id=capability.capability_id,
            capability_version=capability.version,
            capability_definition_id=capability.id,
            initiated_by_user_id=user.id,
            extension_installation_id=capability.installation_id,
            status="running",
            deadline_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        db.add(execution)
        db.commit()

    token_headers = execution_headers(test_db, execution_id)
    with test_db() as db:
        execution = db.get(Execution, execution_id)
        execution.deadline_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    with test_db() as db:
        assert expire_due_executions(db) == 1
        db.commit()
    with test_db() as db:
        assert expire_due_executions(db) == 0
        assert db.get(Execution, execution_id).status == "expired"
        events = list(
            db.query(ExecutionEvent).filter(ExecutionEvent.execution_id == execution_id)
        )
        assert [event.type for event in events] == ["execution.expired"]

    response = TestClient(app).post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=token_headers,
        json={
            "events": [
                {
                    "producerSource": "deadline.agent",
                    "producerEventId": "too-late",
                    "type": "execution.completed",
                    "schemaUri": "urn:fair:event:execution.completed:v1",
                    "payload": {},
                }
            ]
        },
    )
    assert response.status_code == 401


def test_extension_cannot_project_a_message_into_another_thread(test_db):
    user = _user()
    with test_db() as db:
        db.add(user)
        capability = add_agent_capability(
            db, ExtensionInstallation(extension_id="owned-message.agent")
        )
        db.commit()
        capability_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    own_thread = client.post("/api/v1/threads", json={"title": "Own"}).json()
    other_thread = client.post("/api/v1/threads", json={"title": "Other"}).json()
    turn = client.post(
        f"/api/v1/threads/{own_thread['id']}/turns",
        json={
            "content": "hello",
            "capabilityDefinitionId": str(capability_id),
        },
    ).json()
    response = client.post(
        f"/api/v1/executions/{turn['executionId']}/events/ingest",
        headers=execution_headers(test_db, turn["executionId"]),
        json={
            "events": [
                {
                    "producerSource": "owned-message.agent",
                    "producerEventId": "cross-thread-message",
                    "type": "message.started",
                    "schemaUri": "urn:fair:event:message.started:v1",
                    "payload": {
                        "messageId": str(uuid4()),
                        "threadId": other_thread["id"],
                        "role": "assistant",
                        "authorType": "extension",
                    },
                }
            ]
        },
    )
    assert response.status_code == 422
    assert "thread_id must match" in response.json()["detail"]

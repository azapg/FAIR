from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import ExtensionClient, User, UserRole
from fair_platform.backend.main import app
from fair_platform.backend.services.extension_auth import hash_extension_secret


def test_v2_turn_execution_and_event_replay_api(test_db):
    user = User(
        id=uuid4(),
        name="API v2 user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread_response = client.post(
            "/api/v1/threads",
            json={"title": "API thread"},
        )
        assert thread_response.status_code == 201, thread_response.text
        thread = thread_response.json()

        turn_response = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "Hello from the API",
                "clientRequestId": "api-request-1",
            },
        )
        assert turn_response.status_code == 202, turn_response.text
        turn = turn_response.json()

        execution_response = client.get(f"/api/v1/executions/{turn['executionId']}")
        assert execution_response.status_code == 200, execution_response.text
        assert execution_response.json()["status"] == "queued"

        initial_events = client.get(
            f"/api/v1/executions/{turn['executionId']}/events"
        )
        assert initial_events.status_code == 200, initial_events.text
        assert [event["type"] for event in initial_events.json()] == [
            "execution.created"
        ]

        message_id = str(uuid4())
        part_id = str(uuid4())
        event_response = client.post(
            f"/api/v1/executions/{turn['executionId']}/events",
            json={
                "events": [
                    {
                        "producerSource": "api-test",
                        "producerEventId": "started",
                        "type": "execution.started",
                        "schemaUri": "urn:fair:event:execution.started:v1",
                        "payload": {},
                    },
                    {
                        "producerSource": "api-test",
                        "producerEventId": "message-started",
                        "type": "message.started",
                        "schemaUri": "urn:fair:event:message.started:v1",
                        "payload": {
                            "messageId": message_id,
                            "role": "assistant",
                            "authorType": "platform",
                            "ordinal": 1,
                        },
                    },
                    {
                        "producerSource": "api-test",
                        "producerEventId": "message-delta",
                        "type": "message.delta",
                        "schemaUri": "urn:fair:event:message.delta:v1",
                        "payload": {
                            "messageId": message_id,
                            "partId": part_id,
                            "partType": "text",
                            "ordinal": 1,
                            "text": "Hello back",
                        },
                    },
                    {
                        "producerSource": "api-test",
                        "producerEventId": "message-completed",
                        "type": "message.completed",
                        "schemaUri": "urn:fair:event:message.completed:v1",
                        "payload": {"messageId": message_id},
                    },
                    {
                        "producerSource": "api-test",
                        "producerEventId": "completed",
                        "type": "execution.completed",
                        "schemaUri": "urn:fair:event:execution.completed:v1",
                        "payload": {"outputSummary": {"answer": "ok"}},
                    },
                ]
            },
        )
        assert event_response.status_code == 202, event_response.text
        assert [event["sequence"] for event in event_response.json()] == [2, 3, 4, 5, 6]

        replay = client.get(
            f"/api/v1/executions/{turn['executionId']}/events?after_sequence=3"
        )
        assert replay.status_code == 200, replay.text
        assert [event["sequence"] for event in replay.json()] == [4, 5, 6]

        completed = client.get(f"/api/v1/executions/{turn['executionId']}")
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "completed"
        assert completed.json()["snapshot"]["eventCount"] == 6
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_extension_event_ingestion_requires_scope_and_matching_installation(test_db):
    user = User(
        id=uuid4(),
        name="Extension API user",
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
                    secret_hash=hash_extension_secret("extension-secret"),
                    scopes=["executions:events"],
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread = client.post("/api/v1/threads", json={"title": "Extension thread"}).json()
        turn_response = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "Run the extension",
                "clientRequestId": "extension-request-1",
                "target": "mock.extension",
            },
        )
        assert turn_response.status_code == 202, turn_response.text
        execution_id = turn_response.json()["executionId"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    ingestion = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers={
            "X-FAIR-Extension-Id": "mock.extension",
            "Authorization": "Bearer extension-secret",
        },
        json={
            "events": [
                {
                    "producerSource": "mock.extension",
                    "producerEventId": "extension-started",
                    "type": "execution.started",
                    "schemaUri": "urn:fair:event:execution.started:v1",
                    "payload": {},
                }
            ]
        },
    )
    assert ingestion.status_code == 202, ingestion.text
    assert ingestion.json()[0]["producerSource"] == "mock.extension"

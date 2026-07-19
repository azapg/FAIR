from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Enrollment,
    ExtensionInstallation,
    Execution,
    User,
    UserRole,
)
from fair_platform.backend.main import app
from tests.execution_protocol_helpers import (
    add_agent_capability,
    execution_headers,
)


def test_turn_execution_and_event_replay_api(test_db):
    user = User(
        id=uuid4(),
        name="Execution API user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="agent.default")
        session.add(user)
        capability = add_agent_capability(session, installation)
        manifest_snapshot = dict(capability.manifest_snapshot)
        manifest_snapshot["inputSchema"] = {
            "type": "object",
            "additionalProperties": False,
        }
        capability.manifest_snapshot = manifest_snapshot
        session.commit()
        capability_definition_id = capability.id

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
                "capabilityDefinitionId": str(capability_definition_id),
                "input": {},
            },
        )
        assert turn_response.status_code == 202, turn_response.text
        turn = turn_response.json()
        repeated_turn = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "Hello from the API",
                "clientRequestId": "api-request-1",
                "capabilityDefinitionId": str(capability_definition_id),
                "input": {},
            },
        )
        assert repeated_turn.status_code == 202
        assert repeated_turn.json()["id"] == turn["id"]
        conflicting_turn = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "Different request",
                "clientRequestId": "api-request-1",
                "capabilityDefinitionId": str(capability_definition_id),
                "input": {},
            },
        )
        assert conflicting_turn.status_code == 409
        with test_db() as session:
            assert session.get(Execution, UUID(turn["executionId"])).input == {}

        execution_response = client.get(f"/api/v1/executions/{turn['executionId']}")
        assert execution_response.status_code == 200, execution_response.text
        assert execution_response.json()["status"] == "queued"

        refreshed = client.post(
            f"/api/v1/executions/{turn['executionId']}/authorization/refresh",
            headers=execution_headers(test_db, turn["executionId"]),
        )
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["accessToken"]
        assert refreshed.json()["scopes"] == ["executions:events"]

        initial_events = client.get(f"/api/v1/executions/{turn['executionId']}/events")
        assert initial_events.status_code == 200, initial_events.text
        assert [event["type"] for event in initial_events.json()] == [
            "execution.created"
        ]

        message_id = str(uuid4())
        part_id = str(uuid4())
        event_response = client.post(
            f"/api/v1/executions/{turn['executionId']}/events/ingest",
            headers=execution_headers(test_db, turn["executionId"]),
            json={
                "events": [
                    {
                        "producerSource": "agent.default",
                        "producerEventId": "started",
                        "type": "execution.started",
                        "schemaUri": "urn:fair:event:execution.started:v1",
                        "payload": {},
                    },
                    {
                        "producerSource": "agent.default",
                        "producerEventId": "message-started",
                        "type": "message.started",
                        "schemaUri": "urn:fair:event:message.started:v1",
                        "payload": {
                            "messageId": message_id,
                            "role": "assistant",
                            "authorType": "extension",
                            "ordinal": 1,
                        },
                    },
                    {
                        "producerSource": "agent.default",
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
                        "producerSource": "agent.default",
                        "producerEventId": "message-completed",
                        "type": "message.completed",
                        "schemaUri": "urn:fair:event:message.completed:v1",
                        "payload": {"messageId": message_id},
                    },
                    {
                        "producerSource": "agent.default",
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


def test_thread_rejects_spoofed_or_inconsistent_educational_scope(test_db):
    outsider = User(
        id=uuid4(),
        name="Outsider",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    instructor = User(
        id=uuid4(),
        name="Instructor",
        email=f"{uuid4()}@example.test",
        role=UserRole.professor,
    )
    first_course = Course(
        id=uuid4(),
        name="First",
        instructor_id=instructor.id,
        enrollment_code=f"A{str(uuid4())[:7]}",
    )
    second_course = Course(
        id=uuid4(),
        name="Second",
        instructor_id=instructor.id,
        enrollment_code=f"B{str(uuid4())[:7]}",
    )
    assignment = Assignment(
        id=uuid4(),
        course_id=first_course.id,
        title="Scoped assignment",
        max_grade={"value": 100},
    )
    with test_db() as session:
        session.add_all([outsider, instructor, first_course, second_course, assignment])
        session.commit()

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: outsider
    assert (
        client.post(
            "/api/v1/threads",
            json={"title": "Spoofed", "courseId": str(first_course.id)},
        ).status_code
        == 403
    )
    with test_db() as session:
        session.add(
            Enrollment(
                id=uuid4(),
                user_id=outsider.id,
                course_id=first_course.id,
            )
        )
        session.get(Assignment, assignment.id).status = "draft"
        session.commit()
    hidden_draft = client.post(
        "/api/v1/threads",
        json={"title": "Hidden draft", "assignmentId": str(assignment.id)},
    )
    assert hidden_draft.status_code == 404
    app.dependency_overrides[get_current_user] = lambda: instructor
    inconsistent = client.post(
        "/api/v1/threads",
        json={
            "title": "Inconsistent",
            "courseId": str(second_course.id),
            "assignmentId": str(assignment.id),
        },
    )
    assert inconsistent.status_code == 422
    app.dependency_overrides.pop(get_current_user, None)


def test_successful_output_must_match_the_pinned_capability_schema(test_db):
    user = User(
        id=uuid4(),
        name="Output schema user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        capability = add_agent_capability(
            session,
            ExtensionInstallation(extension_id="agent.typed-output"),
        )
        snapshot = dict(capability.manifest_snapshot)
        snapshot["outputSchema"] = {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        }
        capability.manifest_snapshot = snapshot
        session.commit()
        capability_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread = client.post("/api/v1/threads", json={"title": "Typed"}).json()
        turn = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "answer",
                "capabilityDefinitionId": str(capability_id),
            },
        ).json()
        rejected = client.post(
            f"/api/v1/executions/{turn['executionId']}/events/ingest",
            headers=execution_headers(test_db, turn["executionId"]),
            json={
                "events": [
                    {
                        "producerSource": "agent.typed-output",
                        "producerEventId": "bad-output",
                        "type": "execution.completed",
                        "schemaUri": "urn:fair:event:execution.completed:v1",
                        "payload": {"outputSummary": {"answer": 42}},
                    }
                ]
            },
        )
        assert rejected.status_code == 422
        assert "Capability output at answer is invalid" in rejected.json()["detail"]
        assert (
            client.get(f"/api/v1/executions/{turn['executionId']}").json()["status"]
            == "queued"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_extension_event_ingestion_uses_execution_scoped_authority(test_db):
    user = User(
        id=uuid4(),
        name="Extension API user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        installation = ExtensionInstallation(extension_id="mock.extension")
        session.add(user)
        capability = add_agent_capability(session, installation)
        session.commit()
        capability_definition_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread = client.post(
            "/api/v1/threads", json={"title": "Extension thread"}
        ).json()
        turn_response = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "Run the extension",
                "clientRequestId": "extension-request-1",
                "capabilityDefinitionId": str(capability_definition_id),
            },
        )
        assert turn_response.status_code == 202, turn_response.text
        execution_id = turn_response.json()["executionId"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    ingestion = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=execution_headers(test_db, execution_id),
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

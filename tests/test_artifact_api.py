from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    Artifact,
    ArtifactVersion,
    Assignment,
    Course,
    Enrollment,
    ExecutionDispatchOutbox,
    ExtensionInstallation,
    User,
    UserRole,
)
from fair_platform.backend.main import app
from tests.execution_protocol_helpers import add_agent_capability, execution_headers
from fair_platform.backend.services.execution_protocol import build_execution_command


def test_artifact_api_creates_draft_finalizes_and_reads_hashed_version(test_db):
    user = User(
        id=uuid4(),
        name="Artifact API user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        artifact_response = client.post(
            "/api/v1/artifacts",
            json={
                "title": "Feedback artifact",
                "kindUri": "urn:fair:artifact:feedback",
                "description": "A structured feedback document",
            },
        )
        assert artifact_response.status_code == 201, artifact_response.text
        artifact = artifact_response.json()
        assert artifact["versions"] == []

        version_response = client.post(
            f"/api/v1/artifacts/{artifact['id']}/versions",
            json={
                "schemaUri": "urn:fair:schema:feedback:v1",
                "parts": [
                    {
                        "name": "feedback.json",
                        "role": "semantic",
                        "mediaType": "application/json",
                        "inlineJson": {"b": 2, "a": 1},
                    }
                ],
            },
        )
        assert version_response.status_code == 201, version_response.text
        draft = version_response.json()
        assert draft["state"] == "draft"
        assert draft["parts"][0]["ordinal"] == 1
        assert draft["contentHash"] is None

        finalized_response = client.post(
            f"/api/v1/artifact-versions/{draft['id']}/finalize"
        )
        assert finalized_response.status_code == 200, finalized_response.text
        finalized = finalized_response.json()
        assert finalized["state"] == "finalized"
        assert finalized["hashAlgorithm"] == "sha-256"
        assert finalized["contentHash"]
        assert finalized["parts"][0]["contentHash"]
        assert finalized["parts"][0]["sizeBytes"] > 0

        link_response = client.post(
            f"/api/v1/artifact-versions/{draft['id']}/links",
            json={
                "relationship": "derived_from",
                "targetType": "artifact_version",
                "targetId": draft["id"],
                "metadata": {"reason": "self-contained provenance fixture"},
            },
        )
        assert link_response.status_code == 201, link_response.text
        assert link_response.json()["targetId"] == draft["id"]

        links_response = client.get(f"/api/v1/artifact-versions/{draft['id']}/links")
        assert links_response.status_code == 200, links_response.text
        assert len(links_response.json()) == 1

        read_response = client.get(f"/api/v1/artifacts/{artifact['id']}")
        assert read_response.status_code == 200, read_response.text
        read_artifact = read_response.json()
        assert read_artifact["currentVersionId"] == draft["id"]
        assert read_artifact["versions"][0]["state"] == "finalized"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_extension_can_create_a_provenance_stamped_artifact_for_its_execution(test_db):
    user = User(
        id=uuid4(),
        name="Extension artifact user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        capability = add_agent_capability(
            session,
            ExtensionInstallation(extension_id="artifact.extension"),
            requested_scopes=["artifacts:write"],
        )
        session.commit()
        capability_definition_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    thread = client.post("/api/v1/threads", json={"title": "Artifact thread"}).json()
    turn = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={
            "content": "produce feedback",
            "capabilityDefinitionId": str(capability_definition_id),
        },
    ).json()
    execution_id = turn["executionId"]

    created = client.post(
        f"/api/v1/executions/{execution_id}/artifacts",
        headers=execution_headers(test_db, execution_id),
        json={
            "title": "Extension feedback",
            "kindUri": "urn:fair:artifact:feedback",
            "version": {
                "schemaUri": "urn:fair:schema:feedback:v1",
                "parts": [
                    {
                        "name": "feedback.json",
                        "role": "semantic",
                        "mediaType": "application/json",
                        "inlineJson": {"score": 0.9},
                    }
                ],
            },
            "finalize": True,
            "clientRequestId": "artifact-request-1",
        },
    )
    assert created.status_code == 201, created.text
    artifact = created.json()
    version = artifact["versions"][0]
    assert version["state"] == "finalized"
    assert version["producingExecutionId"] == execution_id
    assert version["createdByExtensionInstallationId"]

    repeated = client.post(
        f"/api/v1/executions/{execution_id}/artifacts",
        headers=execution_headers(test_db, execution_id),
        json={
            "title": "Extension feedback",
            "kindUri": "urn:fair:artifact:feedback",
            "version": {
                "schemaUri": "urn:fair:schema:feedback:v1",
                "parts": [
                    {
                        "name": "feedback.json",
                        "role": "semantic",
                        "mediaType": "application/json",
                        "inlineJson": {"score": 0.9},
                    }
                ],
            },
            "finalize": True,
            "clientRequestId": "artifact-request-1",
        },
    )
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == artifact["id"]

    conflicting = client.post(
        f"/api/v1/executions/{execution_id}/artifacts",
        headers=execution_headers(test_db, execution_id),
        json={
            "title": "Different feedback",
            "kindUri": "urn:fair:artifact:feedback",
            "version": {
                "parts": [
                    {
                        "name": "feedback.json",
                        "role": "semantic",
                        "mediaType": "application/json",
                        "inlineJson": {"score": 1},
                    }
                ]
            },
            "clientRequestId": "artifact-request-1",
        },
    )
    assert conflicting.status_code == 409

    untrusted_storage = client.post(
        f"/api/v1/executions/{execution_id}/artifacts",
        headers=execution_headers(test_db, execution_id),
        json={
            "title": "Untrusted storage reference",
            "kindUri": "urn:fair:artifact:feedback",
            "version": {
                "parts": [
                    {
                        "name": "feedback.json",
                        "role": "semantic",
                        "mediaType": "application/json",
                        "storageUri": "local://another-users-object",
                    }
                ]
            },
            "clientRequestId": "artifact-request-storage",
        },
    )
    assert untrusted_storage.status_code == 422

    events = client.get(f"/api/v1/executions/{execution_id}/events")
    assert events.status_code == 200, events.text
    assert [event["type"] for event in events.json()] == [
        "execution.created",
        "artifact.created",
    ]
    app.dependency_overrides.pop(get_current_user, None)


def test_execution_command_freezes_typed_assignment_artifact_access(test_db):
    user = User(
        id=uuid4(),
        name="Artifact input user",
        email=f"{uuid4()}@example.test",
        role=UserRole.professor,
    )
    course = Course(
        id=uuid4(),
        name="Artifact course",
        instructor_id=user.id,
        enrollment_code=f"A{str(uuid4())[:7]}",
        is_enrollment_enabled=True,
    )
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Artifact assignment",
        max_grade={"value": 100},
    )
    pinned_artifact = Artifact(
        id=uuid4(),
        title="Prompt",
        artifact_type="document",
        kind_uri="urn:fair:artifact:assignment-prompt",
        creator_id=user.id,
        owner_user_id=user.id,
        assignment_id=assignment.id,
        status="attached",
    )
    unrelated_artifact = Artifact(
        id=uuid4(),
        title="Unrelated",
        artifact_type="document",
        creator_id=user.id,
        owner_user_id=user.id,
        status="attached",
    )
    with test_db() as session:
        session.add_all([user, course, assignment, pinned_artifact, unrelated_artifact])
        capability = add_agent_capability(
            session,
            ExtensionInstallation(extension_id="artifact-reader.agent"),
            requested_scopes=["artifacts:read"],
        )
        session.commit()
        capability_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    thread = client.post(
        "/api/v1/threads",
        json={
            "title": "Assignment context",
            "courseId": str(course.id),
            "assignmentId": str(assignment.id),
        },
    ).json()
    turn = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={
            "content": "Read the prompt",
            "capabilityDefinitionId": str(capability_id),
        },
    ).json()
    execution_id = turn["executionId"]

    with test_db() as session:
        dispatch = (
            session.query(ExecutionDispatchOutbox)
            .filter(ExecutionDispatchOutbox.execution_id == UUID(execution_id))
            .one()
        )
        command = build_execution_command(session, dispatch)
        assert [item.artifact_id for item in command.execution.artifacts] == [
            pinned_artifact.id
        ]
        assert command.execution.artifacts[0].download_path.endswith(
            f"/{pinned_artifact.id}/download"
        )

    headers = execution_headers(test_db, execution_id)
    with test_db() as session:
        late_version = ArtifactVersion(
            id=uuid4(),
            artifact_id=pinned_artifact.id,
            ordinal=1,
            metadata_json={"late": True},
            created_by_user_id=user.id,
        )
        session.add(late_version)
        session.flush()
        session.get(Artifact, pinned_artifact.id).current_version_id = late_version.id
        session.commit()
    allowed = client.get(
        f"/api/v1/executions/{execution_id}/artifacts/{pinned_artifact.id}",
        headers=headers,
    )
    denied = client.get(
        f"/api/v1/executions/{execution_id}/artifacts/{unrelated_artifact.id}",
        headers=headers,
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["id"] == str(pinned_artifact.id)
    assert allowed.json()["versions"] == []
    assert denied.status_code == 404


def test_execution_freezes_only_artifacts_visible_to_its_initiating_user(test_db):
    instructor = User(
        id=uuid4(),
        name="Artifact owner",
        email=f"{uuid4()}@example.test",
        role=UserRole.professor,
    )
    student = User(
        id=uuid4(),
        name="Artifact reader",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    course = Course(
        id=uuid4(),
        name="Artifact access course",
        instructor_id=instructor.id,
        enrollment_code=f"C{str(uuid4())[:7]}",
    )
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Artifact access assignment",
        max_grade={"value": 100},
    )
    visible = Artifact(
        id=uuid4(),
        title="Visible prompt",
        artifact_type="document",
        creator_id=instructor.id,
        owner_user_id=instructor.id,
        course_id=course.id,
        assignment_id=assignment.id,
        access_level="assignment",
    )
    private = Artifact(
        id=uuid4(),
        title="Instructor notes",
        artifact_type="document",
        creator_id=instructor.id,
        owner_user_id=instructor.id,
        course_id=course.id,
        assignment_id=assignment.id,
        access_level="private",
    )
    with test_db() as session:
        session.add_all(
            [
                instructor,
                student,
                course,
                assignment,
                Enrollment(id=uuid4(), user_id=student.id, course_id=course.id),
                visible,
                private,
            ]
        )
        capability = add_agent_capability(
            session,
            ExtensionInstallation(extension_id="artifact-isolation.agent"),
            requested_scopes=["artifacts:read"],
        )
        session.commit()
        capability_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: student
    client = TestClient(app)
    thread = client.post(
        "/api/v1/threads",
        json={
            "title": "Visible resources only",
            "assignmentId": str(assignment.id),
        },
    ).json()
    turn = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={
            "content": "Read my resources",
            "capabilityDefinitionId": str(capability_id),
        },
    ).json()
    with test_db() as session:
        dispatch = (
            session.query(ExecutionDispatchOutbox)
            .filter(ExecutionDispatchOutbox.execution_id == UUID(turn["executionId"]))
            .one()
        )
        command = build_execution_command(session, dispatch)
        assert [item.artifact_id for item in command.execution.artifacts] == [
            visible.id
        ]
    app.dependency_overrides.pop(get_current_user, None)

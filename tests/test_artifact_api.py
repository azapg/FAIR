from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    ExtensionClient,
    ExtensionInstallation,
    User,
    UserRole,
)
from fair_platform.backend.main import app
from fair_platform.backend.services.extension_auth import hash_extension_secret


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

        links_response = client.get(
            f"/api/v1/artifact-versions/{draft['id']}/links"
        )
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
    now = datetime.now(timezone.utc)
    with test_db() as session:
        session.add_all(
            [
                user,
                ExtensionClient(
                    extension_id="artifact.extension",
                    secret_hash=hash_extension_secret("artifact-secret"),
                    scopes=["executions:events", "artifacts:write"],
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                ),
                ExtensionInstallation(extension_id="artifact.extension"),
            ]
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    thread = client.post("/api/v1/threads", json={"title": "Artifact thread"}).json()
    turn = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={"content": "produce feedback", "target": "artifact.extension"},
    ).json()
    execution_id = turn["executionId"]

    created = client.post(
        f"/api/v1/executions/{execution_id}/artifacts",
        headers={
            "X-FAIR-Extension-Id": "artifact.extension",
            "Authorization": "Bearer artifact-secret",
        },
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
        headers={
            "X-FAIR-Extension-Id": "artifact.extension",
            "Authorization": "Bearer artifact-secret",
        },
        json={
            "title": "Extension feedback",
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
            "finalize": True,
            "clientRequestId": "artifact-request-1",
        },
    )
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == artifact["id"]

    events = client.get(f"/api/v1/executions/{execution_id}/events")
    assert events.status_code == 200, events.text
    assert [event["type"] for event in events.json()] == [
        "execution.created",
        "artifact.created",
    ]
    app.dependency_overrides.pop(get_current_user, None)

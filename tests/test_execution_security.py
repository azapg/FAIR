from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    ExecutionDispatchOutbox,
    ExtensionGrant,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    GrantDecision,
    User,
    UserRole,
)
from fair_platform.backend.main import app
from fair_platform.backend.services.extension_grants import resolve_extension_effects
from fair_platform.backend.services.execution_projection import append_and_project_event
from tests.execution_protocol_helpers import add_agent_capability, execution_headers


def test_turn_rejects_unknown_and_disabled_targets_and_user_events_cannot_spoof(
    test_db,
):
    user = User(
        id=uuid4(),
        name="Boundary user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        disabled_capability = add_agent_capability(
            session,
            ExtensionInstallation(
                extension_id="disabled.extension",
                status=ExtensionInstallationStatus.disabled,
            ),
        )
        enabled_capability = add_agent_capability(
            session, ExtensionInstallation(extension_id="enabled.extension")
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread = client.post("/api/v1/threads", json={"title": "Boundary"}).json()
        unknown = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={"content": "no", "capabilityDefinitionId": str(uuid4())},
        )
        assert unknown.status_code == 404, unknown.text
        disabled = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "no",
                "capabilityDefinitionId": str(disabled_capability.id),
            },
        )
        assert disabled.status_code == 409, disabled.text

        turn = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "yes",
                "capabilityDefinitionId": str(enabled_capability.id),
            },
        ).json()
        execution_id = turn["executionId"]
        spoof = client.post(
            f"/api/v1/executions/{execution_id}/events",
            json={
                "events": [
                    {
                        "producerSource": "fair.platform",
                        "producerEventId": "spoof-complete",
                        "type": "execution.completed",
                        "schemaUri": "urn:fair:event:execution.completed:v1",
                        "payload": {},
                    }
                ]
            },
        )
        assert spoof.status_code == 403, spoof.text

        feedback = client.post(
            f"/api/v1/executions/{execution_id}/events",
            json={
                "events": [
                    {
                        "producerSource": "spoofed.extension",
                        "producerEventId": "feedback-1",
                        "type": "user.feedback",
                        "schemaUri": "urn:fair:event:user.feedback:v1",
                        "visibility": "private",
                        "payload": {"rating": 1},
                    }
                ]
            },
        )
        assert feedback.status_code == 202, feedback.text
        assert feedback.json()[0]["producerSource"] == f"user:{user.id}"
        assert feedback.json()[0]["visibility"] == "user"

        with test_db() as session:
            append_and_project_event(
                session,
                execution_id=UUID(execution_id),
                producer_source="enabled.extension",
                producer_event_id="private-diagnostic",
                event_type="extension.diagnostic",
                schema_uri="urn:fair:event:extension.diagnostic:v1",
                visibility="private",
                payload={"secret": "must-not-leak"},
            )
            session.commit()
        replay = client.get(f"/api/v1/executions/{execution_id}/events")
        assert replay.status_code == 200
        assert "private-diagnostic" not in {
            event["producerEventId"] for event in replay.json()
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_extension_grants_are_deny_by_default_and_deny_wins(test_db):
    installation_id = uuid4()
    capability_id = uuid4()
    with test_db() as session:
        installation = ExtensionInstallation(
            id=installation_id,
            extension_id="grant.test",
            status=ExtensionInstallationStatus.enabled,
        )
        capability = CapabilityDefinition(
            id=capability_id,
            installation_id=installation_id,
            capability_id="grading.v1",
            surface="flow.step",
            version="1.0.0",
        )
        session.add_all(
            [
                installation,
                capability,
                ExtensionGrant(
                    installation_id=installation_id,
                    effect="grade:write",
                    decision=GrantDecision.allow,
                    reason="course-wide approval",
                ),
                ExtensionGrant(
                    installation_id=installation_id,
                    capability_definition_id=capability_id,
                    effect="grade:write",
                    decision=GrantDecision.deny,
                    reason="this capability is read-only here",
                ),
            ]
        )
        session.commit()

        scoped = resolve_extension_effects(
            session,
            installation_id=installation_id,
            effects=("grade:write", "artifact:read"),
            capability_definition_id=capability_id,
        )
        global_scope = resolve_extension_effects(
            session,
            installation_id=installation_id,
            effects=("grade:write",),
        )

        assert scoped["grade:write"].allowed is False
        assert scoped["grade:write"].denying_grant_ids
        assert scoped["artifact:read"].allowed is False
        assert global_scope["grade:write"].allowed is True

        installation.status = ExtensionInstallationStatus.revoked
        session.commit()
        revoked = resolve_extension_effects(
            session,
            installation_id=installation_id,
            effects=("grade:write",),
        )
        assert revoked["grade:write"].allowed is False


def test_invalid_event_batch_is_atomic_and_terminal_execution_rejects_new_events(
    test_db,
):
    user = User(
        id=uuid4(),
        name="Security API user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        capability = add_agent_capability(
            session, ExtensionInstallation(extension_id="security.extension")
        )
        session.commit()
        capability_definition_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread = client.post(
            "/api/v1/threads", json={"title": "Security thread"}
        ).json()
        turn = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "security",
                "capabilityDefinitionId": str(capability_definition_id),
            },
        ).json()
        execution_id = turn["executionId"]
        authority_headers = execution_headers(test_db, execution_id)

        response = client.post(
            f"/api/v1/executions/{execution_id}/events/ingest",
            headers=authority_headers,
            json={
                "events": [
                    {
                        "producerSource": "security.extension",
                        "producerEventId": "valid-before-invalid",
                        "type": "execution.started",
                        "schemaUri": "urn:fair:event:execution.started:v1",
                        "payload": {},
                    },
                    {
                        "producerSource": "security.extension",
                        "producerEventId": "invalid-message",
                        "type": "message.delta",
                        "schemaUri": "urn:fair:event:message.delta:v1",
                        "payload": {},
                    },
                ]
            },
        )
        assert response.status_code == 422, response.text
        events = client.get(f"/api/v1/executions/{execution_id}/events").json()
        assert [event["type"] for event in events] == ["execution.created"]

        completed = client.post(
            f"/api/v1/executions/{execution_id}/events/ingest",
            headers=authority_headers,
            json={
                "events": [
                    {
                        "producerSource": "security.extension",
                        "producerEventId": "complete",
                        "type": "execution.completed",
                        "schemaUri": "urn:fair:event:execution.completed:v1",
                        "payload": {},
                    }
                ]
            },
        )
        assert completed.status_code == 202, completed.text
        terminal = client.post(
            f"/api/v1/executions/{execution_id}/events/ingest",
            headers=authority_headers,
            json={
                "events": [
                    {
                        "producerSource": "security.extension",
                        "producerEventId": "after-terminal",
                        "type": "execution.started",
                        "schemaUri": "urn:fair:event:execution.started:v1",
                        "payload": {},
                    }
                ]
            },
        )
        assert terminal.status_code == 401, terminal.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_interaction_resolution_is_user_owned_and_extension_cannot_finalize_it(test_db):
    user = User(
        id=uuid4(),
        name="Interaction API user",
        email=f"{uuid4()}@example.test",
        role=UserRole.student,
    )
    with test_db() as session:
        session.add(user)
        capability = add_agent_capability(
            session,
            ExtensionInstallation(extension_id="interaction.extension"),
            supports_resume=True,
        )
        session.commit()
        capability_definition_id = capability.id

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        thread = client.post(
            "/api/v1/threads", json={"title": "Interaction thread"}
        ).json()
        turn = client.post(
            f"/api/v1/threads/{thread['id']}/turns",
            json={
                "content": "ask me",
                "capabilityDefinitionId": str(capability_definition_id),
            },
        ).json()
        execution_id = turn["executionId"]
        authority_headers = execution_headers(test_db, execution_id)
        interaction_id = str(uuid4())

        requested = client.post(
            f"/api/v1/executions/{execution_id}/events/ingest",
            headers=authority_headers,
            json={
                "events": [
                    {
                        "producerSource": "interaction.extension",
                        "producerEventId": "interaction-requested",
                        "type": "interaction.requested",
                        "schemaUri": "urn:fair:event:interaction.requested:v1",
                        "payload": {
                            "interactionId": interaction_id,
                            "kind": "confirmation",
                            "schema": {"type": "object"},
                            "message": "Approve?",
                        },
                    }
                ]
            },
        )
        assert requested.status_code == 202, requested.text

        listed = client.get(f"/api/v1/executions/{execution_id}/interactions")
        assert listed.status_code == 200, listed.text
        assert listed.json()[0]["status"] == "pending"

        extension_resolution = client.post(
            f"/api/v1/executions/{execution_id}/events/ingest",
            headers=authority_headers,
            json={
                "events": [
                    {
                        "producerSource": "interaction.extension",
                        "producerEventId": "extension-resolution",
                        "type": "interaction.resolved",
                        "schemaUri": "urn:fair:event:interaction.resolved:v1",
                        "payload": {"interactionId": interaction_id},
                    }
                ]
            },
        )
        assert extension_resolution.status_code == 403, extension_resolution.text

        resolved = client.post(
            f"/api/v1/interactions/{interaction_id}/resolve",
            json={
                "status": "resolved",
                "response": {"approved": True},
                "clientRequestId": "resolve-1",
            },
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["status"] == "resolved"
        assert resolved.json()["resolvedByUserId"] == str(user.id)
        repeated = client.post(
            f"/api/v1/interactions/{interaction_id}/resolve",
            json={
                "status": "resolved",
                "response": {"approved": True},
                "clientRequestId": "resolve-1",
            },
        )
        assert repeated.status_code == 200, repeated.text
        conflicting = client.post(
            f"/api/v1/interactions/{interaction_id}/resolve",
            json={
                "status": "resolved",
                "response": {"approved": False},
                "clientRequestId": "resolve-1",
            },
        )
        assert conflicting.status_code == 409
        with test_db() as session:
            resume_commands = list(
                session.query(ExecutionDispatchOutbox).filter(
                    ExecutionDispatchOutbox.execution_id == UUID(execution_id),
                    ExecutionDispatchOutbox.command_kind == "resume",
                )
            )
            assert len(resume_commands) == 1
            assert resume_commands[0].payload == {
                "interactionId": interaction_id,
                "status": "resolved",
                "response": {"approved": True},
            }
    finally:
        app.dependency_overrides.pop(get_current_user, None)

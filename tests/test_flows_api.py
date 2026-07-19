from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExecutionDispatchOutbox,
    ExtensionInstallation,
    FlowVersion,
)
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.main import app
from fair_platform.backend.services.flow_service import _flow_allocation_lock_statement
from fair_platform.backend.services.execution_projection import (
    rebuild_execution_projection,
)
from tests.execution_protocol_helpers import execution_headers


def _user(test_db, email: str) -> User:
    with test_db() as session:
        user = User(
            id=uuid4(),
            name=email,
            email=email,
            role=UserRole.professor,
            password_hash="unused",
            is_verified=True,
        )
        session.add(user)
        session.commit()
        return user


def _as_user(user: User):
    app.dependency_overrides[get_current_user] = lambda: user


def _capability(
    test_db, extension_id: str = "test.flow-extension"
) -> tuple[CapabilityDefinition, str]:
    with test_db() as session:
        resolved_extension_id = f"{extension_id}.{uuid4()}"
        installation = ExtensionInstallation(
            extension_id=resolved_extension_id,
            display_name="Flow test Extension",
            version="1.0.0",
        )
        session.add(installation)
        session.flush()
        capability = CapabilityDefinition(
            installation_id=installation.id,
            capability_id="test.transform",
            kind="action",
            version="1.0.0",
            declared_effects=[],
            manifest_snapshot={
                "capabilityId": "test.transform",
                "kind": "action",
                "version": "1.0.0",
                "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"},
            },
        )
        session.add(capability)
        session.commit()
        return capability, resolved_extension_id


def _definition(capability: CapabilityDefinition, *node_ids: str) -> dict:
    return {
        "mode": "ordered",
        "nodes": [
            {
                "id": node_id,
                "capabilityDefinitionId": str(capability.id),
            }
            for node_id in node_ids
        ],
    }


def test_flow_crud_is_owner_scoped(test_db):
    owner = _user(test_db, "flow-owner@example.test")
    stranger = _user(test_db, "flow-stranger@example.test")
    client = TestClient(app)

    _as_user(owner)
    created = client.post(
        "/api/v1/flows", json={"name": "Grade submissions", "description": "v1"}
    )
    assert created.status_code == 201
    flow_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/flows/{flow_id}", json={"name": "Grade deterministically"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Grade deterministically"
    assert len(client.get("/api/v1/flows").json()) == 1

    _as_user(stranger)
    assert client.get(f"/api/v1/flows/{flow_id}").status_code == 404
    assert (
        client.patch(f"/api/v1/flows/{flow_id}", json={"name": "Mine"}).status_code
        == 404
    )

    _as_user(owner)
    archived = client.delete(f"/api/v1/flows/{flow_id}")
    assert archived.status_code == 200
    assert archived.json()["archivedAt"] is not None
    assert client.get("/api/v1/flows").json() == []
    assert len(client.get("/api/v1/flows?include_archived=true").json()) == 1


def test_flow_versions_are_ordered_and_have_explicit_lifecycle(test_db):
    owner = _user(test_db, "version-owner@example.test")
    capability, _ = _capability(test_db)
    _as_user(owner)
    client = TestClient(app)
    flow_id = client.post("/api/v1/flows", json={"name": "Ordered"}).json()["id"]

    first = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": _definition(capability, "one")},
    )
    second = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": _definition(capability, "one", "two")},
    )
    assert first.status_code == second.status_code == 201
    assert [first.json()["ordinal"], second.json()["ordinal"]] == [1, 2]
    assert first.json()["definitionHash"] != second.json()["definitionHash"]

    same_definition_with_config = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={
            "definition": _definition(capability, "one"),
            "configSnapshot": {"threshold": 0.8},
        },
    )
    assert same_definition_with_config.status_code == 201
    assert same_definition_with_config.json()["ordinal"] == 3
    assert (
        same_definition_with_config.json()["definitionHash"]
        != first.json()["definitionHash"]
    )

    version_id = first.json()["id"]
    published = client.post(f"/api/v1/flows/{flow_id}/versions/{version_id}/publish")
    assert published.status_code == 200
    assert published.json()["state"] == "published"
    assert (
        client.post(
            f"/api/v1/flows/{flow_id}/versions/{version_id}/publish"
        ).status_code
        == 409
    )

    archived = client.post(f"/api/v1/flows/{flow_id}/versions/{version_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["state"] == "archived"
    assert (
        client.post(
            f"/api/v1/flows/{flow_id}/versions/{version_id}/archive"
        ).status_code
        == 409
    )

    with test_db() as session:
        stored = session.get(FlowVersion, UUID(version_id))
        assert stored is not None
        stored.definition = {"nodes": []}
        try:
            session.flush()
        except ValueError:
            session.rollback()
        else:
            raise AssertionError("archived FlowVersion accepted a content mutation")


def test_flow_version_ordinal_allocation_locks_flow_on_postgresql():
    statement = _flow_allocation_lock_statement(uuid4())
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql


def test_start_flow_creates_pinned_root_execution_and_outbox(test_db):
    owner = _user(test_db, "execution-owner@example.test")
    capability, _ = _capability(test_db, "execution-extension")
    _as_user(owner)
    client = TestClient(app)
    flow_id = client.post("/api/v1/flows", json={"name": "Executable"}).json()["id"]
    draft = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": _definition(capability, "step")},
    ).json()

    assert (
        client.post(f"/api/v1/flows/{flow_id}/executions", json={}).status_code == 409
    )
    client.post(f"/api/v1/flows/{flow_id}/versions/{draft['id']}/publish")
    started = client.post(
        f"/api/v1/flows/{flow_id}/executions",
        json={"flowVersionId": draft["id"], "input": {"submissionId": "s-1"}},
    )
    assert started.status_code == 202
    body = started.json()
    assert body["flowVersionId"] == draft["id"]
    assert body["status"] == "running"

    with test_db() as session:
        execution = session.get(Execution, UUID(body["executionId"]))
        step = session.get(Execution, UUID(body["stepExecutionId"]))
        dispatch = session.get(ExecutionDispatchOutbox, UUID(body["dispatchId"]))
        assert execution is not None
        assert execution.root_execution_id == execution.id
        assert str(execution.flow_version_id) == draft["id"]
        assert execution.input == {"submissionId": "s-1"}
        assert execution.status == "running"
        assert step is not None
        assert step.parent_execution_id == execution.id
        assert step.root_execution_id == execution.id
        assert step.flow_node_id == "step"
        assert step.capability_id == "test.transform"
        assert dispatch is not None
        assert dispatch.execution_id == step.id
        assert dispatch.target.startswith("execution-extension.")
        assert dispatch.payload["capability_id"] == "test.transform"


def test_two_step_flow_advances_from_events_and_replays_deterministically(test_db):
    owner = _user(test_db, "two-step-owner@example.test")
    capability, extension_id = _capability(test_db, "two-step-extension")
    _as_user(owner)
    client = TestClient(app)
    flow_id = client.post("/api/v1/flows", json={"name": "Two steps"}).json()["id"]
    version = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": _definition(capability, "first", "second")},
    ).json()
    assert (
        client.post(
            f"/api/v1/flows/{flow_id}/versions/{version['id']}/publish"
        ).status_code
        == 200
    )
    started = client.post(f"/api/v1/flows/{flow_id}/executions", json={})
    assert started.status_code == 202, started.text
    root_id = UUID(started.json()["executionId"])
    first_id = UUID(started.json()["stepExecutionId"])

    def complete(execution_id: UUID, event_id: str, output: dict) -> None:
        response = client.post(
            f"/api/v1/executions/{execution_id}/events/ingest",
            headers=execution_headers(test_db, execution_id),
            json={
                "events": [
                    {
                        "producerSource": extension_id,
                        "producerEventId": event_id,
                        "type": "execution.completed",
                        "schemaUri": "urn:fair:event:execution.completed:v1",
                        "occurredAt": datetime.now(timezone.utc).isoformat(),
                        "visibility": "user",
                        "payload": {"outputSummary": output},
                    }
                ]
            },
        )
        assert response.status_code == 202, response.text

    complete(first_id, "first-completed", {"value": 1})
    with test_db() as session:
        children = list(
            session.query(Execution)
            .filter(Execution.parent_execution_id == root_id)
            .order_by(Execution.created_at)
        )
        assert [child.flow_node_id for child in children] == ["first", "second"]
        second = children[1]
        second_id = second.id
        assert second.input["previousOutput"] == {"value": 1}

    complete(second_id, "second-completed", {"value": 2})
    with test_db() as session:
        root = session.get(Execution, root_id)
        assert root is not None
        assert root.status == "completed"
        assert root.output_summary["output"] == {"value": 2}
        assert len(root.output_summary["nodeResults"]) == 2
        snapshot = rebuild_execution_projection(session, root.id)
        session.commit()
        assert snapshot.projection["status"] == "completed"
        assert (
            len(
                list(
                    session.query(Execution).filter(
                        Execution.parent_execution_id == root_id
                    )
                )
            )
            == 2
        )

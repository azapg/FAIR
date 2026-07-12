from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import Execution, ExecutionDispatchOutbox, FlowVersion
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.main import app
from fair_platform.backend.services.flow_service import _flow_allocation_lock_statement


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
    assert client.patch(f"/api/v1/flows/{flow_id}", json={"name": "Mine"}).status_code == 404

    _as_user(owner)
    archived = client.delete(f"/api/v1/flows/{flow_id}")
    assert archived.status_code == 200
    assert archived.json()["archivedAt"] is not None
    assert client.get("/api/v1/flows").json() == []
    assert len(client.get("/api/v1/flows?include_archived=true").json()) == 1


def test_flow_versions_are_ordered_and_have_explicit_lifecycle(test_db):
    owner = _user(test_db, "version-owner@example.test")
    _as_user(owner)
    client = TestClient(app)
    flow_id = client.post("/api/v1/flows", json={"name": "Ordered"}).json()["id"]

    first = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": {"nodes": [{"id": "one"}]}},
    )
    second = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": {"nodes": [{"id": "one"}, {"id": "two"}]}},
    )
    assert first.status_code == second.status_code == 201
    assert [first.json()["ordinal"], second.json()["ordinal"]] == [1, 2]
    assert first.json()["definitionHash"] != second.json()["definitionHash"]

    same_definition_with_pin = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={
            "definition": {"nodes": [{"id": "one"}]},
            "capabilityPins": [{"capabilityId": "grade", "version": "1.0.0"}],
            "configSnapshot": {"threshold": 0.8},
        },
    )
    assert same_definition_with_pin.status_code == 201
    assert same_definition_with_pin.json()["ordinal"] == 3
    assert same_definition_with_pin.json()["definitionHash"] != first.json()["definitionHash"]

    version_id = first.json()["id"]
    published = client.post(f"/api/v1/flows/{flow_id}/versions/{version_id}/publish")
    assert published.status_code == 200
    assert published.json()["state"] == "published"
    assert client.post(f"/api/v1/flows/{flow_id}/versions/{version_id}/publish").status_code == 409

    archived = client.post(f"/api/v1/flows/{flow_id}/versions/{version_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["state"] == "archived"
    assert client.post(f"/api/v1/flows/{flow_id}/versions/{version_id}/archive").status_code == 409

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
    _as_user(owner)
    client = TestClient(app)
    flow_id = client.post("/api/v1/flows", json={"name": "Executable"}).json()["id"]
    draft = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        json={"definition": {"nodes": [{"id": "step", "capability": "grade"}]}},
    ).json()

    assert client.post(f"/api/v1/flows/{flow_id}/executions", json={}).status_code == 409
    client.post(f"/api/v1/flows/{flow_id}/versions/{draft['id']}/publish")
    started = client.post(
        f"/api/v1/flows/{flow_id}/executions",
        json={"flowVersionId": draft["id"], "input": {"submissionId": "s-1"}},
    )
    assert started.status_code == 202
    body = started.json()
    assert body["flowVersionId"] == draft["id"]
    assert body["status"] == "queued"

    with test_db() as session:
        execution = session.get(Execution, UUID(body["executionId"]))
        dispatch = session.get(ExecutionDispatchOutbox, UUID(body["dispatchId"]))
        assert execution is not None
        assert execution.root_execution_id == execution.id
        assert str(execution.flow_version_id) == draft["id"]
        assert execution.input == {"submissionId": "s-1"}
        assert dispatch is not None
        assert dispatch.target == "flow.executor"
        assert dispatch.payload["flowVersionId"] == draft["id"]

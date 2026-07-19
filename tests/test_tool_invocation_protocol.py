from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExecutionDispatchOutbox,
    ExtensionInstallation,
    User,
)
from fair_platform.backend.main import app
from tests.execution_protocol_helpers import (
    add_agent_capability,
    execution_headers,
)


def _tool_capability(session, capability_id: str = "calculator.add"):
    installation = ExtensionInstallation(
        id=uuid4(),
        extension_id=f"tool.{capability_id.replace('.', '-')}",
        delivery_mode="runner",
        status="enabled",
    )
    session.add(installation)
    session.flush()
    capability = CapabilityDefinition(
        id=uuid4(),
        installation_id=installation.id,
        capability_id=capability_id,
        kind="tool",
        version="1.0.0",
        requested_scopes=[],
        declared_effects=[],
        tool_capabilities=[],
        manifest_snapshot={
            "capabilityId": capability_id,
            "kind": "tool",
            "version": "1.0.0",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            },
        },
    )
    session.add(capability)
    session.flush()
    return capability


def test_agent_invokes_only_declared_platform_tool_with_idempotent_child_execution(
    test_db,
):
    user = User(id=uuid4(), name="Tool User", email=f"{uuid4()}@test", role="user")
    with test_db() as db:
        db.add(user)
        parent_capability = add_agent_capability(
            db,
            ExtensionInstallation(
                extension_id="tool-using.agent", delivery_mode="runner"
            ),
            requested_scopes=["tools:invoke"],
            tool_capabilities=["calculator.add"],
        )
        tool = _tool_capability(db)
        undeclared_tool = _tool_capability(db, "calculator.subtract")
        db.commit()
        parent_capability_id = parent_capability.id
        tool_id = tool.id
        undeclared_tool_id = undeclared_tool.id

    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    thread = client.post("/api/v1/threads", json={"title": "Tools"}).json()
    turn = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={
            "content": "add numbers",
            "capabilityDefinitionId": str(parent_capability_id),
        },
    ).json()
    parent_id = turn["executionId"]
    headers = execution_headers(test_db, parent_id)

    denied = client.post(
        f"/api/v1/executions/{parent_id}/tools",
        headers=headers,
        json={
            "capabilityDefinitionId": str(undeclared_tool_id),
            "idempotencyKey": "tool-call-denied",
            "input": {"a": 5, "b": 2},
        },
    )
    assert denied.status_code == 403

    request = {
        "capabilityDefinitionId": str(tool_id),
        "idempotencyKey": "tool-call-1",
        "input": {"a": 2, "b": 3},
    }
    created = client.post(
        f"/api/v1/executions/{parent_id}/tools",
        headers=headers,
        json=request,
    )
    repeated = client.post(
        f"/api/v1/executions/{parent_id}/tools",
        headers=headers,
        json=request,
    )
    assert created.status_code == repeated.status_code == 202
    conflicting = client.post(
        f"/api/v1/executions/{parent_id}/tools",
        headers=headers,
        json={**request, "input": {"a": 9, "b": 9}},
    )
    assert conflicting.status_code == 409
    child_id = created.json()["executionId"]
    assert repeated.json()["executionId"] == child_id
    with test_db() as db:
        children = list(
            db.query(Execution).filter(
                Execution.parent_execution_id == UUID(parent_id),
                Execution.idempotency_key == "tool-call-1",
            )
        )
        assert len(children) == 1
        assert children[0].root_execution_id == UUID(parent_id)
        dispatches = list(
            db.query(ExecutionDispatchOutbox).filter(
                ExecutionDispatchOutbox.execution_id == UUID(child_id)
            )
        )
        assert len(dispatches) == 1

    completed = client.post(
        f"/api/v1/executions/{child_id}/events/ingest",
        headers=execution_headers(test_db, child_id),
        json={
            "events": [
                {
                    "producerSource": "tool.calculator-add",
                    "producerEventId": "tool-completed",
                    "type": "execution.completed",
                    "schemaUri": "urn:fair:event:execution.completed:v1",
                    "payload": {"outputSummary": {"result": 5}},
                }
            ]
        },
    )
    assert completed.status_code == 202, completed.text
    result = client.get(
        f"/api/v1/executions/{parent_id}/tools/{child_id}",
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json() == {
        "executionId": child_id,
        "status": "completed",
        "output": {"result": 5},
        "errorCode": None,
        "errorSummary": None,
    }

    wrong_turn_kind = client.post(
        f"/api/v1/threads/{thread['id']}/turns",
        json={
            "content": "do not accept tools as chat agents",
            "capabilityDefinitionId": str(tool_id),
        },
    )
    assert wrong_turn_kind.status_code == 422

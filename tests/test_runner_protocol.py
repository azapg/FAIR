from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExecutionDispatchOutbox,
    ExtensionClient,
    ExtensionInstallation,
    Thread,
    Turn,
    User,
)
from fair_platform.backend.main import app
from fair_platform.backend.services.extension_auth import hash_extension_secret


def _seed_runner(test_db, *, client_scopes=("runner:commands",)):
    now = datetime.now(timezone.utc)
    user = User(id=uuid4(), name="Runner User", email=f"{uuid4()}@test", role="user")
    installation = ExtensionInstallation(
        id=uuid4(),
        extension_id="local.research-agent",
        delivery_mode="runner",
        status="enabled",
    )
    capability = CapabilityDefinition(
        id=uuid4(),
        installation_id=installation.id,
        capability_id="agent.chat",
        kind="agent",
        version="1.0.0",
        requested_scopes=["artifacts:read"],
        declared_effects=[],
        manifest_snapshot={
            "capabilityId": "agent.chat",
            "kind": "agent",
            "version": "1.0.0",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            },
            "outputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            },
        },
    )
    thread = Thread(id=uuid4(), owner_user_id=user.id, title="Runner protocol")
    turn = Turn(
        id=uuid4(),
        thread_id=thread.id,
        ordinal=1,
        client_request_id="runner-protocol-turn",
        created_by_user_id=user.id,
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
        extension_installation_id=installation.id,
        thread_id=thread.id,
        turn_id=turn.id,
        status="queued",
        input={"content": "hello"},
    )
    dispatch = ExecutionDispatchOutbox(
        id=uuid4(),
        execution_id=execution.id,
        command_kind="start",
        job_id="logical-command-1",
        target=installation.extension_id,
        payload={"content": "hello"},
        status="pending",
    )
    client = ExtensionClient(
        extension_id=installation.extension_id,
        secret_hash=hash_extension_secret("runner-secret"),
        scopes=list(client_scopes),
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    with test_db() as db:
        db.add_all(
            [user, thread, turn, installation, capability, execution, dispatch, client]
        )
        db.commit()
    return dispatch.id


def _headers():
    return {
        "X-FAIR-Extension-Id": "local.research-agent",
        "Authorization": "Bearer runner-secret",
    }


def test_runner_claims_transport_neutral_command_and_acknowledges_exact_lease(test_db):
    dispatch_id = _seed_runner(test_db)
    client = TestClient(app)

    claimed = client.post(
        "/api/v1/extensions/runner/commands/claim",
        headers=_headers(),
        json={"runnerId": "research-laptop", "waitSeconds": 0, "leaseSeconds": 30},
    )
    assert claimed.status_code == 200, claimed.text
    lease = claimed.json()
    assert lease["command"]["commandId"] == str(dispatch_id)
    assert lease["command"]["idempotencyKey"] == "logical-command-1"
    assert lease["command"]["execution"]["capability"]["capabilityId"] == "agent.chat"
    assert lease["command"]["authorization"]["scopes"] == [
        "artifacts:read",
        "executions:events",
    ]

    wrong_ack = client.post(
        f"/api/v1/extensions/runner/commands/{dispatch_id}/ack",
        headers=_headers(),
        json={"leaseId": str(uuid4())},
    )
    assert wrong_ack.status_code == 409
    ack = client.post(
        f"/api/v1/extensions/runner/commands/{dispatch_id}/ack",
        headers=_headers(),
        json={"leaseId": lease["leaseId"]},
    )
    assert ack.status_code == 204, ack.text
    assert (
        client.post(
            f"/api/v1/extensions/runner/commands/{dispatch_id}/ack",
            headers=_headers(),
            json={"leaseId": lease["leaseId"]},
        ).status_code
        == 204
    )

    assert (
        client.post(
            "/api/v1/extensions/runner/commands/claim",
            headers=_headers(),
            json={"runnerId": "research-laptop", "waitSeconds": 0},
        ).status_code
        == 204
    )


def test_expired_runner_lease_redelivers_same_logical_command(test_db):
    dispatch_id = _seed_runner(test_db)
    client = TestClient(app)
    first = client.post(
        "/api/v1/extensions/runner/commands/claim",
        headers=_headers(),
        json={"runnerId": "runner-a", "waitSeconds": 0, "leaseSeconds": 10},
    ).json()
    with test_db() as db:
        dispatch = db.get(ExecutionDispatchOutbox, dispatch_id)
        dispatch.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    second_response = client.post(
        "/api/v1/extensions/runner/commands/claim",
        headers=_headers(),
        json={"runnerId": "runner-b", "waitSeconds": 0, "leaseSeconds": 10},
    )
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()
    assert second["leaseId"] != first["leaseId"]
    assert second["command"]["commandId"] == first["command"]["commandId"]
    assert second["command"]["idempotencyKey"] == first["command"]["idempotencyKey"]


def test_runner_credential_requires_only_runner_command_scope(test_db):
    _seed_runner(test_db, client_scopes=())
    response = TestClient(app).post(
        "/api/v1/extensions/runner/commands/claim",
        headers=_headers(),
        json={"runnerId": "research-laptop", "waitSeconds": 0},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Missing extension scopes: runner:commands"


def test_runner_cannot_claim_a_new_command_for_terminal_execution(test_db):
    dispatch_id = _seed_runner(test_db)
    with test_db() as db:
        dispatch = db.get(ExecutionDispatchOutbox, dispatch_id)
        execution = db.get(Execution, dispatch.execution_id)
        execution.status = "completed"
        db.commit()

    response = TestClient(app).post(
        "/api/v1/extensions/runner/commands/claim",
        headers=_headers(),
        json={"runnerId": "research-laptop", "waitSeconds": 0},
    )
    assert response.status_code == 409
    assert "terminal Execution" in response.json()["detail"]
    with test_db() as db:
        assert db.get(ExecutionDispatchOutbox, dispatch_id).status == "dead_letter"

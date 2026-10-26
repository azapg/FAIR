"""Transport-level conformance proof that does not depend on an SDK helper."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import Execution, User
from fair_platform.backend.main import app
from tests.test_runner_protocol import _headers, _seed_runner


def test_raw_http_runner_can_claim_report_replay_and_retry_safely(test_db):
    dispatch_id = _seed_runner(test_db)
    with test_db() as session:
        execution = session.query(Execution).one()
        user = session.get(User, execution.initiated_by_user_id)

    client = TestClient(app)
    claim = client.post(
        "/api/v1/extensions/runner/commands/claim",
        headers=_headers(),
        json={"runnerId": "raw-http-conformance", "waitSeconds": 0},
    )
    assert claim.status_code == 200, claim.text
    lease = claim.json()
    command = lease["command"]
    execution_id = command["execution"]["id"]
    token_headers = {
        "Authorization": f"Bearer {command['authorization']['accessToken']}"
    }
    assert command["protocolVersion"] == "1"
    assert command["commandId"] == str(dispatch_id)
    capability_pin = command["execution"]["capability"]
    assert capability_pin["capabilityId"] == "agent.chat"
    assert capability_pin["version"] == "1.0.0"
    assert capability_pin["extensionId"] == "local.research-agent"
    assert capability_pin["definitionId"]
    assert capability_pin["installationId"]

    ack = client.post(
        f"/api/v1/extensions/runner/commands/{dispatch_id}/ack",
        headers=_headers(),
        json={"leaseId": lease["leaseId"]},
    )
    assert ack.status_code == 204, ack.text

    message_id = str(uuid4())
    part_id = str(uuid4())
    events = [
        {
            "producerSource": "local.research-agent",
            "producerEventId": "raw-started",
            "type": "execution.started",
            "schemaUri": "urn:fair:event:execution.started:v1",
            "payload": {},
        },
        {
            "producerSource": "local.research-agent",
            "producerEventId": "raw-message",
            "type": "message.started",
            "schemaUri": "urn:fair:event:message.started:v1",
            "payload": {
                "messageId": message_id,
                "role": "assistant",
                "authorType": "extension",
            },
        },
        {
            "producerSource": "local.research-agent",
            "producerEventId": "raw-chunk",
            "type": "message.delta",
            "schemaUri": "urn:fair:event:message.delta:v1",
            "payload": {
                "messageId": message_id,
                "partId": part_id,
                "partType": "text",
                "text": "raw protocol works",
            },
        },
        {
            "producerSource": "local.research-agent",
            "producerEventId": "raw-completed",
            "type": "execution.completed",
            "schemaUri": "urn:fair:event:execution.completed:v1",
            "payload": {"outputSummary": {"answer": "ok"}},
        },
    ]
    accepted = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=token_headers,
        json={"events": events},
    )
    assert accepted.status_code == 202, accepted.text
    assert [event["sequence"] for event in accepted.json()] == [1, 2, 3, 4]

    # A network retry of the exact terminal event is idempotent.
    retried = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=token_headers,
        json={"events": [events[-1]]},
    )
    assert retried.status_code == 202, retried.text
    assert retried.json()[0]["sequence"] == 4

    # Reusing a producer identity for different content is a protocol conflict.
    conflicting = dict(events[-1])
    conflicting["payload"] = {"outputSummary": {"answer": "different"}}
    conflict = client.post(
        f"/api/v1/executions/{execution_id}/events/ingest",
        headers=token_headers,
        json={"events": [conflicting]},
    )
    assert conflict.status_code == 409

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        replay = client.get(f"/api/v1/executions/{execution_id}/events")
        assert replay.status_code == 200, replay.text
        assert [event["sequence"] for event in replay.json()] == [1, 2, 3, 4]
        assert client.get(f"/api/v1/executions/{execution_id}").json()["status"] == (
            "completed"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    with test_db() as session:
        assert session.get(Execution, UUID(execution_id)).output_summary == {
            "answer": "ok"
        }

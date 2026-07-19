import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from fair_platform.extension_sdk.contracts.protocol import (
    CapabilityPin,
    DelegatedExecutionAuthorization,
    ExecutionCommand,
    ExecutionDescriptor,
    ExecutionScope,
)
from fair_platform.extension_sdk.execution import ExecutionReporter


def _command(execution_id):
    now = datetime.now(timezone.utc)
    return ExecutionCommand(
        command_id=uuid4(),
        idempotency_key=f"execution:{execution_id}:start:1",
        command="start",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        platform_url="https://fair.test",
        execution=ExecutionDescriptor(
            id=execution_id,
            root_execution_id=execution_id,
            attempt=1,
            kind="agent",
            capability=CapabilityPin(
                definition_id=uuid4(),
                capability_id="agent.chat",
                version="1.0.0",
                installation_id=uuid4(),
                extension_id="mock.extension",
            ),
            scope=ExecutionScope(),
        ),
        authorization=DelegatedExecutionAuthorization(
            access_token="execution-token",
            expires_at=now + timedelta(minutes=15),
            scopes=["executions:events"],
        ),
    )


def test_execution_reporter_emits_shared_event_contract():
    execution_id = uuid4()
    received: list[dict] = []
    server_sequence = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal server_sequence
        assert request.url.path == f"/api/v1/executions/{execution_id}/events/ingest"
        assert request.headers["Authorization"] == "Bearer execution-token"
        body = json.loads(request.content)
        received.extend(body["events"])
        accepted = []
        for event in body["events"]:
            server_sequence += 1
            accepted.append(
                {
                    **event,
                    "id": str(uuid4()),
                    "executionId": str(execution_id),
                    "sequence": server_sequence,
                    "receivedAt": "2026-07-11T00:00:00Z",
                }
            )
        return httpx.Response(202, json=accepted)

    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://fair.test",
        )
        reporter = ExecutionReporter(
            command=_command(execution_id),
            client=client,
        )
        message_id = uuid4()
        part_id = uuid4()
        artifact_id = uuid4()
        artifact_version_id = uuid4()
        interaction_id = uuid4()
        started = await reporter.started()
        delta = await reporter.message_delta(message_id, part_id, "hello")
        artifact = await reporter.artifact_created(
            artifact_id,
            artifact_version_id,
            kind_uri="urn:fair:artifact:feedback",
            media_type="application/json",
        )
        requested = await reporter.interaction_requested(
            interaction_id,
            kind="confirmation",
            schema={"type": "object"},
            message="Approve this feedback?",
        )
        completed = await reporter.completed({"answer": "ok"})
        await reporter.close()

        assert started.sequence == 1
        assert delta.sequence == 2
        assert artifact.sequence == 3
        assert requested.sequence == 4
        assert completed.sequence == 5
        assert [event["producerSource"] for event in received] == [
            "mock.extension",
            "mock.extension",
            "mock.extension",
            "mock.extension",
            "mock.extension",
        ]
        assert received[1]["payload"]["message_id"] == str(message_id)
        assert received[1]["payload"]["part_id"] == str(part_id)
        assert received[2]["type"] == "artifact.created"
        assert received[2]["payload"]["artifact_version_id"] == str(artifact_version_id)
        assert received[3]["payload"]["interaction_id"] == str(interaction_id)

    import asyncio

    asyncio.run(run())


def test_execution_reporter_creates_provenance_stamped_artifacts():
    execution_id = uuid4()
    received: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/executions/{execution_id}/artifacts"
        assert request.headers["Authorization"] == "Bearer execution-token"
        received.update(json.loads(request.content))
        return httpx.Response(201, json={"id": str(uuid4()), "versions": []})

    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://fair.test",
        )
        reporter = ExecutionReporter(
            command=_command(execution_id),
            client=client,
        )
        artifact = await reporter.create_artifact(
            title="Feedback",
            kind_uri="urn:fair:artifact:feedback",
            version={
                "parts": [
                    {
                        "name": "feedback.json",
                        "role": "semantic",
                        "mediaType": "application/json",
                        "inlineJson": {"score": 1},
                    }
                ]
            },
        )
        await reporter.close()
        assert artifact["id"]

    import asyncio

    asyncio.run(run())
    assert received["kindUri"] == "urn:fair:artifact:feedback"
    assert received["finalize"] is True


def test_execution_reporter_chunks_token_streams():
    execution_id = uuid4()
    received: list[dict] = []
    sequence = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal sequence
        body = json.loads(request.content)
        event = body["events"][0]
        received.append(event)
        sequence += 1
        return httpx.Response(
            202,
            json=[
                {
                    **event,
                    "id": str(uuid4()),
                    "executionId": str(execution_id),
                    "sequence": sequence,
                    "receivedAt": "2026-07-14T00:00:00Z",
                }
            ],
        )

    async def tokens():
        for token in ("a", "b", "c", "d", "e"):
            yield token

    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://fair.test",
        )
        reporter = ExecutionReporter(command=_command(execution_id), client=client)
        await reporter.stream_text(
            tokens(),
            message_id=uuid4(),
            part_id=uuid4(),
            max_chars=3,
        )
        await client.aclose()

    import asyncio

    asyncio.run(run())
    assert [event["type"] for event in received] == [
        "message.started",
        "message.delta",
        "message.delta",
        "message.completed",
    ]
    assert (
        "".join(
            event["payload"]["text"]
            for event in received
            if event["type"] == "message.delta"
        )
        == "abcde"
    )

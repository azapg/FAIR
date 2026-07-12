import json
from uuid import uuid4

import httpx

from fair_platform.extension_sdk.auth import ExtensionCredentials
from fair_platform.extension_sdk.execution import ExecutionReporter


def test_execution_reporter_emits_shared_event_contract():
    execution_id = uuid4()
    received: list[dict] = []
    server_sequence = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal server_sequence
        assert request.url.path == f"/api/v1/executions/{execution_id}/events/ingest"
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
            execution_id=execution_id,
            platform_url="https://fair.test",
            credentials=ExtensionCredentials(
                extension_id="mock.extension",
                extension_secret="secret",
            ),
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
        received.update(json.loads(request.content))
        return httpx.Response(201, json={"id": str(uuid4()), "versions": []})

    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://fair.test",
        )
        reporter = ExecutionReporter(
            execution_id=execution_id,
            platform_url="https://fair.test",
            credentials=ExtensionCredentials(
                extension_id="mock.extension",
                extension_secret="secret",
            ),
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

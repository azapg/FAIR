import json
from pathlib import Path

from fair_platform.extension_sdk.contracts.events import ExecutionEventBatch


def test_shared_execution_event_fixture_validates_against_python_contract():
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "specs"
        / "fixtures"
        / "execution-events-v1.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    batch = ExecutionEventBatch.model_validate(fixture)

    assert fixture["contract"] == "fair.execution-event.v1"
    assert [event.type for event in batch.events] == [
        "execution.started",
        "artifact.created",
        "execution.completed",
    ]
    assert [event.producer_sequence for event in batch.events] == [1, 2, 3]

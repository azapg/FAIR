import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fair_platform.extension_sdk.contracts.protocol import ExecutionCommand


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "specs"
    / "fixtures"
    / "execution-command.json"
)


def test_execution_command_fixture_is_strict_and_round_trips() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    command = ExecutionCommand.model_validate(raw)

    assert command.command == "start"
    assert command.execution.capability.capability_id == "assistant.assignment"
    assert command.model_dump(by_alias=True, mode="json") == raw

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExecutionCommand.model_validate({**raw, "surprise": True})


def test_execution_command_rejects_authority_that_expires_too_early() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["authorization"]["expiresAt"] = "2026-07-14T12:01:00Z"
    raw["expiresAt"] = "2026-07-14T12:05:00Z"

    with pytest.raises(ValidationError, match="authorization must cover"):
        ExecutionCommand.model_validate(raw)

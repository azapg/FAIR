from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from fair_platform.backend.core.config import get_api_base_url
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExecutionDispatchOutbox,
    ExtensionInstallation,
    ExtensionInstallationStatus,
)
from fair_platform.backend.services.execution_authorization import issue_execution_token
from fair_platform.backend.services.execution_authorization import (
    TERMINAL_EXECUTION_STATUSES,
)
from fair_platform.extension_sdk.contracts.protocol import (
    CapabilityPin,
    DelegatedExecutionAuthorization,
    ExecutionCommand,
    ExecutionDescriptor,
    ExecutionArtifactReference,
    ExecutionScope,
)


class ExecutionProtocolError(ValueError):
    """An Execution cannot be represented as a safe protocol command."""


def _value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_execution_command(
    session: Session,
    dispatch: ExecutionDispatchOutbox,
    *,
    now: datetime | None = None,
) -> ExecutionCommand:
    """Build the single transport-neutral command from durable platform state."""

    issued_at = now or _utc_now()
    execution = session.get(Execution, dispatch.execution_id)
    if execution is None:
        raise ExecutionProtocolError("dispatch references a missing Execution")
    if _value(execution.status) in TERMINAL_EXECUTION_STATUSES:
        raise ExecutionProtocolError("terminal Execution cannot receive a command")
    installation = session.get(
        ExtensionInstallation, execution.extension_installation_id
    )
    capability = session.get(CapabilityDefinition, execution.capability_definition_id)
    if installation is None or capability is None:
        raise ExecutionProtocolError(
            "Extension execution has no installation and capability pin"
        )
    if (
        _value(installation.status) != ExtensionInstallationStatus.enabled.value
        or capability.installation_id != installation.id
        or execution.capability_id != capability.capability_id
        or execution.capability_version != capability.version
    ):
        raise ExecutionProtocolError("Execution capability pin is no longer valid")

    command_expires_at = issued_at + timedelta(minutes=5)
    if execution.deadline_at is not None:
        deadline = execution.deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        command_expires_at = min(command_expires_at, deadline)
    if command_expires_at <= issued_at:
        raise ExecutionProtocolError("Execution deadline has passed")

    scopes = {"executions:events", *(capability.requested_scopes or [])}
    submission_ids = [item.id for item in execution.submissions]
    input_artifacts = (
        list(execution.input_artifacts) if "artifacts:read" in scopes else []
    )
    issued = issue_execution_token(
        execution=execution,
        installation=installation,
        capability=capability,
        scopes=scopes,
        submission_ids=submission_ids,
        artifact_ids=[item.artifact_id for item in input_artifacts],
        now=issued_at,
    )
    return ExecutionCommand(
        command_id=dispatch.id,
        idempotency_key=dispatch.job_id,
        command=_value(dispatch.command_kind),
        issued_at=issued_at,
        expires_at=command_expires_at,
        platform_url=get_api_base_url(),
        execution=ExecutionDescriptor(
            id=execution.id,
            root_execution_id=execution.root_execution_id,
            parent_execution_id=execution.parent_execution_id,
            attempt=execution.attempt,
            kind=_value(execution.kind),
            capability=CapabilityPin(
                definition_id=capability.id,
                capability_id=capability.capability_id,
                version=capability.version,
                installation_id=installation.id,
                extension_id=installation.extension_id,
            ),
            scope=ExecutionScope(
                course_id=execution.course_id,
                assignment_id=execution.assignment_id,
                submission_ids=submission_ids,
            ),
            deadline_at=execution.deadline_at,
            artifacts=[
                ExecutionArtifactReference(
                    artifact_id=item.artifact_id,
                    artifact_version_id=item.artifact_version_id,
                    download_path=(
                        f"/api/v1/executions/{execution.id}/artifacts/"
                        f"{item.artifact_id}/download"
                    ),
                )
                for item in input_artifacts
            ],
        ),
        authorization=DelegatedExecutionAuthorization(
            access_token=issued.token,
            expires_at=issued.expires_at,
            scopes=list(issued.scopes),
        ),
        payload=dict(dispatch.payload or {}),
        traceparent=execution.trace_id,
    )


__all__ = ["ExecutionProtocolError", "build_execution_command"]

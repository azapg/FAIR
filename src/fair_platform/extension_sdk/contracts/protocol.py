from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator

from fair_platform.extension_sdk.contracts.common import contract_model_config


ProtocolVersion = Literal["1"]
ExecutionCommandName = Literal["start", "resume", "cancel"]


class CapabilityPin(BaseModel):
    """The exact installed capability selected for an Execution."""

    model_config = contract_model_config

    definition_id: UUID
    capability_id: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=128)
    installation_id: UUID
    extension_id: str = Field(min_length=1, max_length=255)


class ExecutionScope(BaseModel):
    """Typed educational scope carried by every command."""

    model_config = contract_model_config

    course_id: UUID | None = None
    assignment_id: UUID | None = None
    submission_ids: list[UUID] = Field(default_factory=list)


class ExecutionArtifactReference(BaseModel):
    """An Artifact the delegated Execution is allowed to read."""

    model_config = contract_model_config

    artifact_id: UUID
    artifact_version_id: UUID | None = None
    download_path: str = Field(min_length=1)


class ExecutionDescriptor(BaseModel):
    """Stable Execution identity and authority context."""

    model_config = contract_model_config

    id: UUID
    root_execution_id: UUID
    parent_execution_id: UUID | None = None
    attempt: int = Field(ge=1)
    kind: str = Field(min_length=1, max_length=32)
    capability: CapabilityPin
    scope: ExecutionScope
    deadline_at: datetime | None = None
    artifacts: list[ExecutionArtifactReference] = Field(default_factory=list)


class DelegatedExecutionAuthorization(BaseModel):
    """Short-lived authority for calls made while handling one Execution."""

    model_config = contract_model_config

    token_type: Literal["Bearer"] = "Bearer"
    access_token: str = Field(min_length=1)
    expires_at: datetime
    scopes: list[str] = Field(default_factory=list)


class ExecutionCommand(BaseModel):
    """The one command envelope shared by webhook and runner delivery."""

    model_config = contract_model_config

    protocol_version: ProtocolVersion = "1"
    command_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=255)
    command: ExecutionCommandName
    issued_at: datetime
    expires_at: datetime
    platform_url: AnyHttpUrl
    execution: ExecutionDescriptor
    authorization: DelegatedExecutionAuthorization
    payload: dict[str, Any] = Field(default_factory=dict)
    traceparent: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def expiry_follows_issue_time(self) -> "ExecutionCommand":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        if self.authorization.expires_at < self.expires_at:
            raise ValueError("delegated authorization must cover the command lifetime")
        return self


class RunnerClaimRequest(BaseModel):
    """Long-poll parameters for an outbound runner."""

    model_config = contract_model_config

    runner_id: str = Field(min_length=1, max_length=255)
    wait_seconds: int = Field(default=20, ge=0, le=30)
    lease_seconds: int = Field(default=30, ge=10, le=300)


class RunnerCommandLease(BaseModel):
    """A leased command returned to an authenticated outbound runner."""

    model_config = contract_model_config

    lease_id: UUID
    lease_expires_at: datetime
    command: ExecutionCommand


class RunnerCommandAck(BaseModel):
    model_config = contract_model_config

    lease_id: UUID


__all__ = [
    "CapabilityPin",
    "DelegatedExecutionAuthorization",
    "ExecutionArtifactReference",
    "ExecutionCommand",
    "ExecutionCommandName",
    "ExecutionDescriptor",
    "ExecutionScope",
    "ProtocolVersion",
    "RunnerClaimRequest",
    "RunnerCommandAck",
    "RunnerCommandLease",
]

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.extension_sdk.contracts.events import (
    ExecutionEventBatch,
    ExecutionEventCreate,
    ExecutionEventRead,
)


class ThreadCreate(BaseModel):
    model_config = schema_config

    title: str | None = Field(default=None, max_length=500)
    course_id: UUID | None = None
    assignment_id: UUID | None = None
    submission_id: UUID | None = None


class ThreadRead(ThreadCreate):
    model_config = schema_config

    id: UUID
    owner_user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class TurnCreate(BaseModel):
    model_config = schema_config

    content: str = Field(min_length=1, max_length=100_000)
    client_request_id: str | None = Field(default=None, max_length=255)
    capability_id: str = Field(default="agent.default", min_length=1, max_length=255)
    target: str = Field(default="agent.default", min_length=1, max_length=255)


class TurnRead(BaseModel):
    model_config = schema_config

    id: UUID
    thread_id: UUID
    ordinal: int
    client_request_id: str
    created_by_user_id: UUID
    status: str
    created_at: datetime
    completed_at: datetime | None
    execution_id: UUID
    user_message_id: UUID


class ExecutionRead(BaseModel):
    model_config = schema_config

    id: UUID
    thread_id: UUID | None
    turn_id: UUID | None
    course_id: UUID | None
    assignment_id: UUID | None
    submission_ids: list[UUID] = Field(default_factory=list)
    parent_execution_id: UUID | None
    root_execution_id: UUID
    retry_of_execution_id: UUID | None
    attempt: int
    kind: str
    capability_id: str | None
    capability_version: str | None
    flow_version_id: UUID | None
    initiated_by_user_id: UUID | None
    extension_installation_id: UUID | None
    status: str
    waiting_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_summary: str | None
    output_summary: dict[str, Any] | None
    snapshot: dict[str, Any] | None = None


class InteractionRead(BaseModel):
    model_config = schema_config

    id: UUID
    execution_id: UUID
    kind: str
    schema_: dict[str, Any] = Field(alias="schema")
    message: str
    choices: list[dict[str, Any]] | None
    target_url: str | None
    status: str
    requested_by_extension_installation_id: UUID | None
    expires_at: datetime | None
    resolved_by_user_id: UUID | None
    response: dict[str, Any] | None
    resolved_at: datetime | None
    created_at: datetime


class InteractionResolve(BaseModel):
    model_config = schema_config

    status: Literal["resolved", "declined"] = "resolved"
    response: dict[str, Any] | None = None
    client_request_id: str | None = Field(default=None, max_length=255)


__all__ = [
    "ExecutionEventBatch",
    "ExecutionEventCreate",
    "ExecutionEventRead",
    "ExecutionRead",
    "InteractionRead",
    "InteractionResolve",
    "ThreadCreate",
    "ThreadRead",
    "TurnCreate",
    "TurnRead",
]

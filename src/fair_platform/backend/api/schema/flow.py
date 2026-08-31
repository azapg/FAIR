from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from fair_platform.backend.api.schema.utils import schema_config


class FlowCreate(BaseModel):
    model_config = schema_config

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    course_id: UUID | None = None


class FlowUpdate(BaseModel):
    model_config = schema_config

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class FlowNodeDefinition(BaseModel):
    model_config = schema_config

    id: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    capability_definition_id: UUID
    input: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=86_400)
    max_attempts: int = Field(default=1, ge=1, le=10)
    on_failure: Literal["fail", "continue"] = "fail"


class FlowDefinition(BaseModel):
    model_config = schema_config

    mode: Literal["ordered"] = "ordered"
    nodes: list[FlowNodeDefinition] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def node_ids_are_unique(self) -> "FlowDefinition":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Flow node IDs must be unique")
        return self


class FlowVersionCreate(BaseModel):
    model_config = schema_config

    definition: FlowDefinition
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class FlowVersionRead(BaseModel):
    model_config = schema_config

    id: UUID
    flow_id: UUID
    ordinal: int
    state: str
    definition: FlowDefinition
    capability_pins: list[dict[str, Any]] = Field(default_factory=list)
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    definition_hash: str
    created_by_user_id: UUID
    created_at: datetime
    published_at: datetime | None
    archived_at: datetime | None


class FlowRead(BaseModel):
    model_config = schema_config

    id: UUID
    owner_user_id: UUID
    course_id: UUID | None
    name: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    versions: list[FlowVersionRead] = Field(default_factory=list)


class FlowExecutionStart(BaseModel):
    model_config = schema_config

    flow_version_id: UUID | None = None
    assignment_id: UUID | None = None
    submission_ids: list[UUID] = Field(default_factory=list)
    input: dict[str, Any] = Field(default_factory=dict)


class FlowExecutionRead(BaseModel):
    model_config = schema_config

    execution_id: UUID
    flow_version_id: UUID
    status: str
    dispatch_id: UUID
    step_execution_id: UUID


__all__ = [
    "FlowCreate",
    "FlowDefinition",
    "FlowExecutionRead",
    "FlowExecutionStart",
    "FlowRead",
    "FlowNodeDefinition",
    "FlowUpdate",
    "FlowVersionCreate",
    "FlowVersionRead",
]

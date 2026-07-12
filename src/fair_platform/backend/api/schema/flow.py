from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

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


class FlowVersionCreate(BaseModel):
    model_config = schema_config

    definition: dict[str, Any]
    capability_pins: list[dict[str, Any]] = Field(default_factory=list)
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class FlowVersionRead(FlowVersionCreate):
    id: UUID
    flow_id: UUID
    ordinal: int
    state: str
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
    input: dict[str, Any] = Field(default_factory=dict)


class FlowExecutionRead(BaseModel):
    model_config = schema_config

    execution_id: UUID
    flow_version_id: UUID
    status: str
    dispatch_id: UUID


__all__ = [
    "FlowCreate",
    "FlowExecutionRead",
    "FlowExecutionStart",
    "FlowRead",
    "FlowUpdate",
    "FlowVersionCreate",
    "FlowVersionRead",
]

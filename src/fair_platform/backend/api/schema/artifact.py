from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.data.models.artifact import (
    ArtifactLinkRelationship,
    ArtifactLinkTargetType,
)


class ArtifactCreate(BaseModel):
    model_config = schema_config

    title: str = Field(min_length=1, max_length=500)
    kind_uri: str = Field(default="urn:fair:artifact:generic", min_length=1, max_length=2048)
    description: str | None = None
    sensitivity: str | None = Field(default=None, max_length=64)
    access_policy: dict[str, Any] | None = None


class ArtifactUpdate(BaseModel):
    model_config = schema_config

    title: str | None = Field(default=None, min_length=1, max_length=500)
    course_id: UUID | None = None
    assignment_id: UUID | None = None
    access_level: str | None = None
    status: str | None = None
    meta: dict[str, Any] | None = None


class ArtifactPartCreate(BaseModel):
    model_config = schema_config

    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=64)
    media_type: str = Field(min_length=1, max_length=255)
    schema_uri: str | None = Field(default=None, max_length=2048)
    storage_uri: str | None = None
    inline_json: dict[str, Any] | None = None
    content_hash: str | None = Field(default=None, max_length=128)
    size_bytes: int | None = Field(default=None, ge=0)
    annotations: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_one_content_source(self) -> "ArtifactPartCreate":
        if (self.storage_uri is None) == (self.inline_json is None):
            raise ValueError("provide exactly one of storage_uri or inline_json")
        return self


class ArtifactVersionCreate(BaseModel):
    model_config = schema_config

    media_type: str | None = Field(default=None, max_length=255)
    schema_uri: str | None = Field(default=None, max_length=2048)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    supersedes_version_id: UUID | None = None
    parts: list[ArtifactPartCreate] = Field(min_length=1, max_length=100)


class ExecutionArtifactCreate(ArtifactCreate):
    model_config = schema_config

    version: ArtifactVersionCreate
    finalize: bool = True
    client_request_id: str | None = Field(default=None, max_length=255)


class ArtifactLinkCreate(BaseModel):
    model_config = schema_config

    relationship: ArtifactLinkRelationship
    target_type: ArtifactLinkTargetType
    target_id: UUID
    metadata: dict[str, Any] | None = None
    created_by_execution_id: UUID | None = None


class ArtifactPartRead(ArtifactPartCreate):
    id: UUID
    artifact_version_id: UUID
    ordinal: int
    hash_algorithm: str | None
    created_at: datetime


class ArtifactLinkRead(BaseModel):
    model_config = schema_config

    id: UUID
    artifact_version_id: UUID
    relationship: ArtifactLinkRelationship
    target_type: ArtifactLinkTargetType
    target_id: UUID
    metadata: dict[str, Any] | None
    created_by_execution_id: UUID | None
    created_at: datetime
    retracted_at: datetime | None


class ArtifactDerivativeRead(BaseModel):
    model_config = schema_config

    id: UUID
    artifact_id: UUID
    derivative_type: str
    storage_uri: str
    mime_type: str
    created_at: datetime
    updated_at: datetime


class ArtifactVersionRead(BaseModel):
    model_config = schema_config

    id: UUID
    artifact_id: UUID
    ordinal: int
    state: str
    media_type: str | None
    schema_uri: str | None
    metadata: dict[str, Any]
    created_by_user_id: UUID | None
    created_by_extension_installation_id: UUID | None
    producing_execution_id: UUID | None
    hash_algorithm: str | None
    content_hash: str | None
    size_bytes: int | None
    provenance: dict[str, Any]
    supersedes_version_id: UUID | None
    created_at: datetime
    finalized_at: datetime | None
    abandoned_at: datetime | None
    parts: list[ArtifactPartRead]
    links: list[ArtifactLinkRead]


class ArtifactRead(BaseModel):
    model_config = schema_config

    id: UUID
    title: str
    artifact_type: str
    mime: str
    meta: dict[str, Any] | None
    status: str
    access_level: str
    course_id: UUID | None
    assignment_id: UUID | None
    kind_uri: str | None
    description: str | None
    owner_user_id: UUID | None
    creator_id: UUID
    sensitivity: str | None
    access_policy: dict[str, Any] | None
    current_version_id: UUID | None
    created_at: datetime
    updated_at: datetime
    derivatives: list[ArtifactDerivativeRead]
    versions: list[ArtifactVersionRead]


__all__ = [
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactDerivativeRead",
    "ExecutionArtifactCreate",
    "ArtifactPartCreate",
    "ArtifactPartRead",
    "ArtifactLinkCreate",
    "ArtifactLinkRead",
    "ArtifactRead",
    "ArtifactVersionCreate",
    "ArtifactVersionRead",
]

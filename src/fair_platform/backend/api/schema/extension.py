from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.extension_sdk.contracts.extension import (
    CapabilityManifest,
    ExtensionManifest,
    JsonSchemaDocument,  # noqa: F401 - public backend schema surface
)


class InstallationCreate(BaseModel):
    model_config = schema_config
    manifest: ExtensionManifest


class InstallationStatusUpdate(BaseModel):
    model_config = schema_config
    status: Literal["enabled", "disabled", "revoked"]


class CapabilityRead(CapabilityManifest):
    id: UUID
    installation_id: UUID
    created_at: datetime


class InstallationRead(BaseModel):
    model_config = schema_config
    id: UUID
    extension_id: str
    display_name: str | None
    version: str | None
    dispatch_url: str | None
    health_url: str | None
    manifest_version: str | None
    status: str
    manifest: ExtensionManifest | None
    capabilities: list[CapabilityRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GrantCreate(BaseModel):
    model_config = schema_config
    installation_id: UUID
    capability_definition_id: UUID | None = None
    course_id: UUID | None = None
    assignment_id: UUID | None = None
    effect: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9._-]*:[a-z][a-z0-9._-]*$")
    decision: Literal["allow", "deny"]
    reason: str | None = Field(default=None, max_length=2000)


class GrantRead(GrantCreate):
    id: UUID
    granted_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


# Client credential administration stays available to the existing router.
class ExtensionClientIssueRequest(BaseModel):
    model_config = schema_config
    extension_id: str = Field(min_length=1)
    scopes: list[str] = Field(default_factory=list)
    enabled: bool = True


class ExtensionClientSecretRead(BaseModel):
    model_config = schema_config
    extension_id: str
    extension_secret: str
    scopes: list[str] = Field(default_factory=list)
    enabled: bool


class ExtensionClientRead(BaseModel):
    model_config = schema_config
    extension_id: str
    scopes: list[str] = Field(default_factory=list)
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ExtensionClientUpdateRequest(BaseModel):
    model_config = schema_config
    scopes: list[str] = Field(default_factory=list)
    enabled: bool


__all__ = [name for name in globals() if not name.startswith("_")]

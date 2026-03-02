from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.utils import schema_config


class ExtensionRegisterRequest(BaseModel):
    model_config = schema_config

    extension_id: str = Field(min_length=1)
    webhook_url: str = Field(min_length=1)
    intents: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    requested_scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtensionRead(BaseModel):
    model_config = schema_config

    extension_id: str
    webhook_url: str
    intents: list[str]
    capabilities: list[str]
    requested_scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any]
    enabled: bool


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


__all__ = [
    "ExtensionRegisterRequest",
    "ExtensionRead",
    "ExtensionClientIssueRequest",
    "ExtensionClientSecretRead",
    "ExtensionClientRead",
]

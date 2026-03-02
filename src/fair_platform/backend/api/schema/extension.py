from datetime import datetime

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.extension_sdk.contracts.extension import (
    ExtensionRead,
    ExtensionRegisterRequest,
)


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


__all__ = [
    "ExtensionRegisterRequest",
    "ExtensionRead",
    "ExtensionClientIssueRequest",
    "ExtensionClientSecretRead",
    "ExtensionClientRead",
    "ExtensionClientUpdateRequest",
]

from typing import Any

from pydantic import BaseModel, Field

from fair_platform.extension_sdk.contracts.common import contract_model_config


class ExtensionRegisterRequest(BaseModel):
    model_config = contract_model_config

    extension_id: str = Field(min_length=1)
    webhook_url: str = Field(min_length=1)
    intents: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    requested_scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtensionRead(BaseModel):
    model_config = contract_model_config

    extension_id: str
    webhook_url: str
    intents: list[str]
    capabilities: list[str]
    requested_scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any]
    enabled: bool


__all__ = ["ExtensionRegisterRequest", "ExtensionRead"]

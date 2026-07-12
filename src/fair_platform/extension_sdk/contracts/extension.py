from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from fair_platform.extension_sdk.contracts.common import contract_model_config


IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class JsonSchemaDocument(BaseModel):
    """A JSON Schema embedded in an extension manifest."""

    model_config = contract_model_config

    schema_: str = Field(default="https://json-schema.org/draft/2020-12/schema", alias="$schema")
    id_: str | None = Field(default=None, alias="$id")
    type: str | list[str]
    title: str | None = None
    description: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    additional_properties: bool | dict[str, Any] | None = Field(
        default=None, alias="additionalProperties"
    )

    @model_validator(mode="after")
    def validate_object_keywords(self) -> "JsonSchemaDocument":
        types = {self.type} if isinstance(self.type, str) else set(self.type)
        if (self.properties or self.required) and "object" not in types:
            raise ValueError("properties and required are only valid for object schemas")
        unknown_required = set(self.required) - set(self.properties)
        if unknown_required:
            raise ValueError(f"required fields lack property definitions: {sorted(unknown_required)}")
        return self


class CapabilityManifest(BaseModel):
    model_config = contract_model_config

    capability_id: str = Field(min_length=1, max_length=255)
    kind: Literal["agent", "grader", "transformer", "tool", "integration"]
    version: str = Field(min_length=1, max_length=128)
    input_schema: JsonSchemaDocument
    output_schema: JsonSchemaDocument
    config_schema: JsonSchemaDocument | None = None
    requested_scopes: list[str] = Field(default_factory=list)
    declared_effects: list[str] = Field(default_factory=list)
    supports_streaming: bool = False
    supports_cancellation: bool = False
    supports_resume: bool = False
    supports_batch: bool = False

    @field_validator("capability_id")
    @classmethod
    def valid_capability_id(cls, value: str) -> str:
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("capability_id must be a lowercase dotted identifier")
        return value

    @field_validator("requested_scopes", "declared_effects")
    @classmethod
    def normalized_unique_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("values must be non-blank and unique")
        return normalized


class ExtensionManifest(BaseModel):
    model_config = contract_model_config

    manifest_version: Literal["1"] = "1"
    extension_id: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=128)
    dispatch_url: HttpUrl
    health_url: HttpUrl | None = None
    capabilities: list[CapabilityManifest] = Field(min_length=1)

    @field_validator("extension_id")
    @classmethod
    def valid_extension_id(cls, value: str) -> str:
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("extension_id must be a lowercase dotted identifier")
        return value

    @model_validator(mode="after")
    def unique_capabilities(self) -> "ExtensionManifest":
        identities = [(item.capability_id, item.version) for item in self.capabilities]
        if len(set(identities)) != len(identities):
            raise ValueError("capability_id and version pairs must be unique")
        return self


# Transitional runtime registration shapes retained until the old in-memory
# registry router is removed from application wiring.
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


__all__ = [
    "CapabilityManifest", "ExtensionManifest", "JsonSchemaDocument",
    "ExtensionRead", "ExtensionRegisterRequest",
]

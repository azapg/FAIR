from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from fair_platform.extension_sdk.contracts.common import contract_model_config


IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class JsonSchemaDocument(BaseModel):
    """A JSON Schema embedded in an extension manifest."""

    # JSON Schema is intentionally extensible; strictness applies to FAIR's
    # envelope, while standard/custom schema keywords must round-trip.
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        extra="allow",
    )

    schema_: str = Field(
        default="https://json-schema.org/draft/2020-12/schema", alias="$schema"
    )
    id_: str | None = Field(default=None, alias="$id")
    type: str | list[str] | None = None
    title: str | None = None
    description: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    additional_properties: bool | dict[str, Any] | None = Field(
        default=None, alias="additionalProperties"
    )

    @model_validator(mode="after")
    def validate_object_keywords(self) -> "JsonSchemaDocument":
        try:
            Draft202012Validator.check_schema(
                self.model_dump(by_alias=True, exclude_none=True)
            )
        except SchemaError as exc:
            raise ValueError(f"invalid JSON Schema: {exc.message}") from exc
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
    tool_capabilities: list[str] = Field(default_factory=list)
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

    @field_validator("requested_scopes", "declared_effects", "tool_capabilities")
    @classmethod
    def normalized_unique_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized) or len(set(normalized)) != len(
            normalized
        ):
            raise ValueError("values must be non-blank and unique")
        return normalized

    @field_validator("tool_capabilities")
    @classmethod
    def valid_tool_capability_ids(cls, values: list[str]) -> list[str]:
        if any(not IDENTIFIER_PATTERN.fullmatch(value) for value in values):
            raise ValueError(
                "tool_capabilities must contain lowercase dotted identifiers"
            )
        return values

    @model_validator(mode="after")
    def tools_require_scope(self) -> "CapabilityManifest":
        if self.tool_capabilities and "tools:invoke" not in self.requested_scopes:
            raise ValueError("tool_capabilities require the tools:invoke scope")
        return self


class ExtensionManifest(BaseModel):
    model_config = contract_model_config

    manifest_version: Literal["1"] = "1"
    extension_id: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=128)
    delivery_mode: Literal["webhook", "runner"] = "webhook"
    dispatch_url: HttpUrl | None = None
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
        if self.delivery_mode == "webhook" and self.dispatch_url is None:
            raise ValueError("webhook delivery requires dispatch_url")
        if self.dispatch_url is not None and self.dispatch_url.scheme != "https":
            raise ValueError(
                "webhook dispatch_url must use HTTPS; use runner mode for local work"
            )
        if self.health_url is not None and self.health_url.scheme != "https":
            raise ValueError("health_url must use HTTPS")
        if self.delivery_mode == "runner" and self.dispatch_url is not None:
            raise ValueError("runner delivery must not define dispatch_url")
        return self


__all__ = [
    "CapabilityManifest",
    "ExtensionManifest",
    "JsonSchemaDocument",
]

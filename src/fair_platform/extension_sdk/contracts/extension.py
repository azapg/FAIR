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


SURFACES = ("chat.agent", "function", "flow.step")

# Schemas a Surface owns on the author's behalf. FAIR still freezes a concrete
# schema onto every CapabilityDefinition; the author simply does not write it.
_ANY_OBJECT: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
}
SURFACE_DEFAULT_SCHEMAS: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "chat.agent": (
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
        _ANY_OBJECT,
    ),
    "function": (_ANY_OBJECT, _ANY_OBJECT),
    "flow.step": (_ANY_OBJECT, _ANY_OBJECT),
}

# Scopes a Surface implies. Authors declare consequential *effects*, not the
# plumbing scopes needed to report their own work.
SURFACE_IMPLIED_SCOPES: dict[str, tuple[str, ...]] = {
    "chat.agent": ("executions:events", "artifacts:read", "artifacts:write"),
    "function": ("executions:events",),
    "flow.step": ("executions:events", "artifacts:read", "artifacts:write"),
}

CONTRACT_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*@\d+$")


class CapabilityManifest(BaseModel):
    model_config = contract_model_config

    capability_id: str = Field(min_length=1, max_length=255)
    surface: Literal["chat.agent", "function", "flow.step"]
    version: str = Field(min_length=1, max_length=128)
    # A FAIR-owned contract id such as "fair.rubric.generate@1". Required for
    # the `function` surface, which is where the contract defines both schemas
    # and the UI placements that render a button for it.
    contract: str | None = None
    display_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2048)
    input_schema: JsonSchemaDocument | None = None
    output_schema: JsonSchemaDocument | None = None
    config_schema: JsonSchemaDocument | None = None
    declared_effects: list[str] = Field(default_factory=list)
    supports_streaming: bool = False
    supports_cancellation: bool = False
    supports_resume: bool = False

    @field_validator("capability_id")
    @classmethod
    def valid_capability_id(cls, value: str) -> str:
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("capability_id must be a lowercase dotted identifier")
        return value

    @field_validator("declared_effects")
    @classmethod
    def normalized_unique_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized) or len(set(normalized)) != len(
            normalized
        ):
            raise ValueError("values must be non-blank and unique")
        return normalized

    @model_validator(mode="after")
    def apply_surface_defaults(self) -> "CapabilityManifest":
        """Let a Surface supply the schemas and scopes the author did not write."""

        if self.surface == "function":
            if not self.contract:
                raise ValueError("the function surface requires a contract id")
            if not CONTRACT_PATTERN.fullmatch(self.contract):
                raise ValueError(
                    "contract must look like 'fair.rubric.generate@1'"
                )
        elif self.contract is not None:
            raise ValueError(f"the {self.surface} surface does not take a contract")

        default_input, default_output = SURFACE_DEFAULT_SCHEMAS[self.surface]
        if self.input_schema is None:
            self.input_schema = JsonSchemaDocument.model_validate(default_input)
        if self.output_schema is None:
            self.output_schema = JsonSchemaDocument.model_validate(default_output)
        return self

    @property
    def requested_scopes(self) -> list[str]:
        """Scopes are implied by the Surface, never hand-declared."""

        return list(SURFACE_IMPLIED_SCOPES[self.surface])


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

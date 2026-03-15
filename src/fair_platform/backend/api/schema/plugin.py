from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.extension_sdk.contracts.plugin import PluginType
from fair_platform.extension_sdk.settings import SettingsSchema


class PluginBase(BaseModel):
    model_config = schema_config

    plugin_id: str
    extension_id: str
    name: str
    plugin_type: PluginType
    action: str
    description: str | None = None
    version: str | None = None
    settings_schema: dict[str, Any] | SettingsSchema = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None
    type: PluginType | None = None
    hash: str | None = None
    source: str | None = None

    @field_validator("settings_schema", mode="before")
    @classmethod
    def _normalize_settings_schema(
        cls,
        value: dict[str, Any] | SettingsSchema,
    ) -> dict[str, Any]:
        if isinstance(value, SettingsSchema):
            return value.to_flat_dict()
        return value

    @field_serializer("settings_schema")
    def _serialize_settings_schema(
        self,
        value: dict[str, Any] | SettingsSchema,
    ) -> dict[str, Any]:
        if isinstance(value, SettingsSchema):
            return value.to_flat_dict()
        return value


class RuntimePlugin(PluginBase):
    settings: dict[str, Any] = Field(default_factory=dict)


__all__ = ["PluginBase", "RuntimePlugin", "PluginType"]

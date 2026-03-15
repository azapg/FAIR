from __future__ import annotations

from typing import Iterable

from fair_platform.backend.api.schema.plugin import RuntimePlugin
from fair_platform.backend.services.extension_registry import LocalExtensionRegistry
from fair_platform.backend.services.settings_validator import validate_settings_schema
from fair_platform.extension_sdk.contracts.plugin import PluginDescriptor, PluginType


def _normalize_plugin(
    raw: dict,
    *,
    extension_id: str,
) -> RuntimePlugin:
    descriptor = PluginDescriptor.model_validate(
        {
            **raw,
            "extension_id": raw.get("extension_id") or extension_id,
        }
    )
    payload = descriptor.model_dump(mode="python")
    payload["settings_schema"] = validate_settings_schema(
        plugin_id=descriptor.plugin_id,
        settings_schema=payload.get("settings_schema", {}),
    )
    payload["id"] = descriptor.plugin_id
    payload["type"] = descriptor.plugin_type
    payload["hash"] = f"{descriptor.extension_id}:{descriptor.plugin_id}"
    payload["source"] = descriptor.extension_id
    return RuntimePlugin.model_validate(payload)


async def list_registered_plugins(
    registry: LocalExtensionRegistry,
    *,
    plugin_type: PluginType | None = None,
) -> list[RuntimePlugin]:
    records = await registry.list()
    plugins: list[RuntimePlugin] = []
    for record in records:
        advertised = record.metadata.get("plugins", []) if isinstance(record.metadata, dict) else []
        if not isinstance(advertised, Iterable):
            continue
        for raw in advertised:
            if not isinstance(raw, dict):
                continue
            plugin = _normalize_plugin(raw, extension_id=record.extension_id)
            if plugin_type and plugin.plugin_type != plugin_type:
                continue
            plugins.append(plugin)
    return plugins


async def get_registered_plugin(
    registry: LocalExtensionRegistry,
    plugin_id: str,
) -> RuntimePlugin | None:
    for plugin in await list_registered_plugins(registry):
        if plugin.plugin_id == plugin_id or plugin.id == plugin_id:
            return plugin
    return None


__all__ = ["get_registered_plugin", "list_registered_plugins"]

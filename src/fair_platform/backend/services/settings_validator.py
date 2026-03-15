from __future__ import annotations

import re
from math import isclose
from typing import Any

from pydantic import ValidationError

from fair_platform.extension_sdk.settings import parse_settings_field

_SETTING_KEY_PATTERN = re.compile(r"^[a-z][a-zA-Z0-9]*$")
_ALIGN_TOLERANCE = 1e-9


class SettingsSchemaValidationError(ValueError):
    def __init__(self, plugin_id: str, issues: list[dict[str, str]]):
        super().__init__("invalid settings schema")
        self.plugin_id = plugin_id
        self.issues = issues


class RuntimeSettingsValidationError(ValueError):
    def __init__(self, plugin_id: str, field: str, reason: str):
        super().__init__(reason)
        self.plugin_id = plugin_id
        self.field = field
        self.reason = reason


class CorruptedSettingsSchemaError(ValueError):
    def __init__(self, plugin_id: str):
        super().__init__("corrupted settings schema")
        self.plugin_id = plugin_id


def validate_settings_schema(
    plugin_id: str,
    settings_schema: Any,
) -> dict[str, dict[str, Any]]:
    issues: list[dict[str, str]] = []
    if not isinstance(settings_schema, dict):
        issues.append(_schema_issue(plugin_id, "settings_schema", "settings_schema must be an object"))
        raise SettingsSchemaValidationError(plugin_id=plugin_id, issues=issues)


    normalized: dict[str, dict[str, Any]] = {}
    for key, raw_field in settings_schema.items():
        if not isinstance(key, str):
            issues.append(_schema_issue(plugin_id, str(key), "setting key must be a string"))
            continue
        if not (1 <= len(key) <= 64):
            issues.append(_schema_issue(plugin_id, key, "setting key length must be between 1 and 64"))
            continue
        if _SETTING_KEY_PATTERN.match(key) is None:
            issues.append(_schema_issue(plugin_id, key, "setting key must match ^[a-z][a-zA-Z0-9]*$"))
            continue
        if not isinstance(raw_field, dict):
            issues.append(_schema_issue(plugin_id, key, "field definition must be an object"))
            continue

        field_type = raw_field.get("fieldType")
        if not isinstance(field_type, str):
            issues.append(_schema_issue(plugin_id, f"{key}.fieldType", "fieldType is required"))
            continue

        try:
            parsed = parse_settings_field(raw_field)
        except ValidationError as exc:
            first = exc.errors()[0]
            location = ".".join(str(part) for part in first.get("loc", ()) if str(part) != field_type)
            path = f"{key}.{location}" if location else key
            issues.append(
                _schema_issue(
                    plugin_id,
                    path,
                    first.get("msg", "invalid field definition"),
                )
            )
            continue

        normalized[key] = parsed.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )

    if issues:
        raise SettingsSchemaValidationError(plugin_id=plugin_id, issues=issues)
    return normalized


def validate_and_hydrate_runtime_settings(
    plugin_id: str,
    settings_schema: Any,
    incoming_settings: Any,
) -> dict[str, Any]:
    try:
        normalized_schema = validate_settings_schema(plugin_id=plugin_id, settings_schema=settings_schema)
    except SettingsSchemaValidationError as exc:
        raise CorruptedSettingsSchemaError(plugin_id=exc.plugin_id) from exc

    if not isinstance(incoming_settings, dict):
        raise RuntimeSettingsValidationError(
            plugin_id=plugin_id,
            field="settings",
            reason="must be an object",
        )

    unknown_keys = sorted(set(incoming_settings) - set(normalized_schema))
    if unknown_keys:
        raise RuntimeSettingsValidationError(
            plugin_id=plugin_id,
            field=unknown_keys[0],
            reason="is not defined in settings_schema",
        )

    hydrated: dict[str, Any] = {}
    for key, field_def in normalized_schema.items():
        required = bool(field_def["required"])
        has_default = "default" in field_def
        if key in incoming_settings:
            value = incoming_settings[key]
            if value is None:
                raise RuntimeSettingsValidationError(
                    plugin_id=plugin_id,
                    field=key,
                    reason="cannot be null",
                )
            _validate_runtime_value(key=key, field_def=field_def, value=value, plugin_id=plugin_id)
            hydrated[key] = value
            continue
        if has_default:
            hydrated[key] = field_def["default"]
            continue
        if required:
            raise RuntimeSettingsValidationError(
                plugin_id=plugin_id,
                field=key,
                reason="is required",
            )
    return hydrated


def _validate_runtime_value(
    *,
    key: str,
    field_def: dict[str, Any],
    value: Any,
    plugin_id: str,
) -> None:
    field_type = field_def["fieldType"]
    if field_type in {"text", "secret", "artifact-ref", "rubric-ref"}:
        if not isinstance(value, str) or not value.strip():
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="must be a non-empty string")
    elif field_type in {"switch", "checkbox"}:
        if not isinstance(value, bool):
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="must be a boolean")
    elif field_type in {"number", "slider"}:
        if not _is_number(value):
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="must be a number")
        minimum = field_def.get("minimum")
        maximum = field_def.get("maximum")
        if minimum is not None and value < minimum:
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="must be greater than or equal to minimum")
        if maximum is not None and value > maximum:
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="must be less than or equal to maximum")
        step = field_def.get("step")
        if step is not None and minimum is not None:
            delta = (value - minimum) / step
            if not isclose(delta, round(delta), abs_tol=_ALIGN_TOLERANCE):
                raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="must align with minimum and step")
    elif field_type == "file":
        if value is None:
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="cannot be null")

    min_length = field_def.get("minLength")
    max_length = field_def.get("maxLength")
    if isinstance(value, str):
        if min_length is not None and len(value) < min_length:
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="is shorter than minLength")
        if max_length is not None and len(value) > max_length:
            raise RuntimeSettingsValidationError(plugin_id=plugin_id, field=key, reason="is longer than maxLength")


def _schema_issue(plugin_id: str, path: str, message: str) -> dict[str, str]:
    return {
        "type": "invalid_settings_schema",
        "plugin_id": plugin_id,
        "message": message,
        "field_path": path,
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


__all__ = [
    "SettingsSchemaValidationError",
    "RuntimeSettingsValidationError",
    "CorruptedSettingsSchemaError",
    "validate_settings_schema",
    "validate_and_hydrate_runtime_settings",
]

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from fair_platform.backend.data.models import CapabilityDefinition


class CapabilityInputError(ValueError):
    pass


class CapabilityOutputError(ValueError):
    pass


def _validate_frozen_schema(
    capability: CapabilityDefinition,
    *,
    schema_field: str,
    value: Any,
    label: str,
    error_type: type[ValueError],
) -> None:
    snapshot = capability.manifest_snapshot or {}
    schema = snapshot.get(schema_field)
    if not isinstance(schema, dict):
        raise error_type(f"Capability has no valid frozen {label} schema")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(value)
    except SchemaError as exc:
        raise error_type(f"Capability {label} schema is invalid") from exc
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "$"
        raise error_type(
            f"Capability {label} at {location} is invalid: {exc.message}"
        ) from exc


def validate_capability_input(
    capability: CapabilityDefinition,
    value: dict[str, Any],
) -> None:
    """Validate input against the schema frozen into the capability pin."""
    _validate_frozen_schema(
        capability,
        schema_field="inputSchema",
        value=value,
        label="input",
        error_type=CapabilityInputError,
    )


def validate_capability_output(
    capability: CapabilityDefinition,
    value: Any,
) -> None:
    """Validate successful output against the exact dispatched capability pin."""
    _validate_frozen_schema(
        capability,
        schema_field="outputSchema",
        value=value,
        label="output",
        error_type=CapabilityOutputError,
    )


__all__ = [
    "CapabilityInputError",
    "CapabilityOutputError",
    "validate_capability_input",
    "validate_capability_output",
]

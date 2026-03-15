from __future__ import annotations

from collections.abc import Iterable
from math import isclose
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from pydantic_core import PydanticUndefined

from fair_platform.extension_sdk.contracts.common import contract_model_config

_SETTING_KEY_PATTERN = r"^[a-z][a-zA-Z0-9]*$"
_DEFAULT_ALIGN_TOLERANCE = 1e-9


class SettingsField(BaseModel):
    model_config = ConfigDict(
        **contract_model_config,
        extra="forbid",
    )

    fieldType: str
    label: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    required: bool
    default: Any = Field(default=PydanticUndefined)

    @model_validator(mode="after")
    def _validate_required_default_relation(self) -> "SettingsField":
        has_default = "default" in self.model_fields_set
        if self.required and has_default:
            raise ValueError("default must not be present when required=true")
        if not self.required and self.fieldType != "file" and not has_default:
            raise ValueError("default is required when required=false")
        if has_default and self.default is None:
            raise ValueError("default cannot be null")
        return self


class TextField(SettingsField):
    fieldType: Literal["text"]
    default: str = Field(default=PydanticUndefined)
    minLength: int | None = Field(default=None, ge=0)
    maxLength: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_text_constraints(self) -> "TextField":
        if self.minLength is not None and self.maxLength is not None and self.minLength > self.maxLength:
            raise ValueError("minLength must be less than or equal to maxLength")
        if "default" in self.model_fields_set:
            value_len = len(self.default)
            if self.minLength is not None and value_len < self.minLength:
                raise ValueError("default must satisfy minLength")
            if self.maxLength is not None and value_len > self.maxLength:
                raise ValueError("default must satisfy maxLength")
        return self


class SecretField(SettingsField):
    fieldType: Literal["secret"]
    default: str = Field(default=PydanticUndefined)
    minLength: int | None = Field(default=None, ge=0)
    maxLength: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_secret_constraints(self) -> "SecretField":
        if self.minLength is not None and self.maxLength is not None and self.minLength > self.maxLength:
            raise ValueError("minLength must be less than or equal to maxLength")
        if "default" in self.model_fields_set:
            value_len = len(self.default)
            if self.minLength is not None and value_len < self.minLength:
                raise ValueError("default must satisfy minLength")
            if self.maxLength is not None and value_len > self.maxLength:
                raise ValueError("default must satisfy maxLength")
        return self


class NumberField(SettingsField):
    fieldType: Literal["number"]
    default: float = Field(default=PydanticUndefined)
    minimum: float
    maximum: float
    step: float | None = None

    @model_validator(mode="after")
    def _validate_number_constraints(self) -> "NumberField":
        if self.minimum > self.maximum:
            raise ValueError("minimum must be less than or equal to maximum")
        if self.step is not None and self.step <= 0:
            raise ValueError("step must be greater than 0")
        if "default" in self.model_fields_set:
            if self.default < self.minimum or self.default > self.maximum:
                raise ValueError("default must be within [minimum, maximum]")
            if self.step is not None:
                delta = (self.default - self.minimum) / self.step
                if not isclose(delta, round(delta), abs_tol=_DEFAULT_ALIGN_TOLERANCE):
                    raise ValueError("default must align with minimum and step")
        return self


class SliderField(SettingsField):
    fieldType: Literal["slider"]
    default: float = Field(default=PydanticUndefined)
    minimum: float
    maximum: float
    step: float = Field(gt=0)
    marks: dict[str, str]

    @model_validator(mode="after")
    def _validate_slider_constraints(self) -> "SliderField":
        if self.minimum > self.maximum:
            raise ValueError("minimum must be less than or equal to maximum")
        if not self.marks:
            raise ValueError("marks must be present and non-empty")
        for key, label in self.marks.items():
            if not isinstance(label, str) or not label.strip():
                raise ValueError("marks labels must be non-empty strings")
            try:
                mark_value = float(key)
            except (TypeError, ValueError) as exc:
                raise ValueError("marks keys must parse as numbers") from exc
            if mark_value < self.minimum or mark_value > self.maximum:
                raise ValueError("marks keys must be within [minimum, maximum]")
        if "default" in self.model_fields_set:
            if self.default < self.minimum or self.default > self.maximum:
                raise ValueError("default must be within [minimum, maximum]")
            delta = (self.default - self.minimum) / self.step
            if not isclose(delta, round(delta), abs_tol=_DEFAULT_ALIGN_TOLERANCE):
                raise ValueError("default must align with minimum and step")
        return self


class SwitchField(SettingsField):
    fieldType: Literal["switch"]
    default: bool = Field(default=PydanticUndefined)


class CheckboxField(SettingsField):
    fieldType: Literal["checkbox"]
    default: bool = Field(default=PydanticUndefined)


class FileField(SettingsField):
    fieldType: Literal["file"]
    allowedTypes: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_file_constraints(self) -> "FileField":
        if "default" in self.model_fields_set:
            raise ValueError("default must not be present for file fields")
        if any(not isinstance(item, str) or not item.strip() for item in self.allowedTypes):
            raise ValueError("allowedTypes entries must be non-empty strings")
        if len(set(self.allowedTypes)) != len(self.allowedTypes):
            raise ValueError("allowedTypes entries must be unique")
        return self


class ArtifactRefField(SettingsField):
    fieldType: Literal["artifact-ref"]
    allowedTypes: list[str] = Field(min_length=1)
    default: str = Field(default=PydanticUndefined)

    @model_validator(mode="after")
    def _validate_artifact_ref_constraints(self) -> "ArtifactRefField":
        if any(not isinstance(item, str) or not item.strip() for item in self.allowedTypes):
            raise ValueError("allowedTypes entries must be non-empty strings")
        if len(set(self.allowedTypes)) != len(self.allowedTypes):
            raise ValueError("allowedTypes entries must be unique")
        if "default" in self.model_fields_set and not self.default.strip():
            raise ValueError("default must be a valid artifact identifier string")
        return self


class RubricRefField(SettingsField):
    fieldType: Literal["rubric-ref"]
    default: str = Field(default=PydanticUndefined)

    @model_validator(mode="after")
    def _validate_rubric_ref_constraints(self) -> "RubricRefField":
        if "default" in self.model_fields_set and not self.default.strip():
            raise ValueError("default must be a valid rubric identifier string")
        return self


SettingsFieldUnion = Annotated[
    TextField
    | SecretField
    | NumberField
    | SliderField
    | SwitchField
    | CheckboxField
    | FileField
    | ArtifactRefField
    | RubricRefField,
    Field(discriminator="fieldType"),
]

_settings_field_adapter = TypeAdapter(SettingsFieldUnion)


def parse_settings_field(raw: Any) -> SettingsFieldUnion:
    return _settings_field_adapter.validate_python(raw)


class SettingsSchema(BaseModel):
    model_config = ConfigDict(
        **contract_model_config,
        extra="forbid",
    )

    properties: dict[str, SettingsFieldUnion] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_keys(self) -> "SettingsSchema":
        for key in self.properties:
            self._validate_key(key)
        return self

    def add(self, key: str, field: SettingsFieldUnion) -> "SettingsSchema":
        self._validate_key(key)
        self.properties[key] = field
        return self

    @classmethod
    def from_pairs(
        cls,
        pairs: Iterable[tuple[str, SettingsFieldUnion]],
    ) -> "SettingsSchema":
        schema = cls()
        for key, field in pairs:
            schema.add(key, field)
        return schema

    def to_flat_dict(self) -> dict[str, Any]:
        return {
            key: value.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            )
            for key, value in self.properties.items()
        }

    @staticmethod
    def _validate_key(key: str) -> None:
        from re import match

        if not isinstance(key, str):
            raise ValueError("setting key must be a string")
        if not (1 <= len(key) <= 64):
            raise ValueError("setting key length must be between 1 and 64")
        if match(_SETTING_KEY_PATTERN, key) is None:
            raise ValueError("setting key must match ^[a-z][a-zA-Z0-9]*$")


__all__ = [
    "SettingsField",
    "TextField",
    "SecretField",
    "NumberField",
    "SliderField",
    "SwitchField",
    "CheckboxField",
    "FileField",
    "ArtifactRefField",
    "RubricRefField",
    "SettingsFieldUnion",
    "SettingsSchema",
    "parse_settings_field",
]

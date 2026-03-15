# Extension Settings Schema - Definitive Specification

Status: Final
Version: 2.0
Date: March 14, 2026
Target: FAIR canary branch

## 1. Purpose

This document defines the canonical plugin settings contract for FAIR.
It is normative and implementation-binding.
Any implementation that deviates from this document is non-compliant.

## 2. Normative Language

The keywords MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, and MAY are to be interpreted as described in RFC 2119.
For this document, SHOULD and MAY are not used for behavior that affects interoperability.

## 3. Canonical Data Model

### 3.1 Root Shape

`settings_schema` MUST be a JSON object where:

- each key is a setting identifier
- each value is a field definition object

Example:

```json
{
  "useOpenAI": {
    "fieldType": "switch",
    "label": "Use OpenAI",
    "description": "Use OpenAI responses API for file transcription.",
    "required": false,
    "default": true
  },
  "openaiModel": {
    "fieldType": "text",
    "label": "OpenAI Model",
    "description": "OpenAI model to use for file transcription.",
    "required": false,
    "default": "gpt-5.4-2026-03-05",
    "minLength": 1,
    "maxLength": 100
  }
}
```

### 3.2 Setting Identifier Rules

Each setting key MUST:

- match regex `^[a-z][a-zA-Z0-9]*$`
- be unique in the object
- be between 1 and 64 characters

### 3.3 Common Field Properties

Every field definition MUST include:

- `fieldType`: one of the supported field types
- `label`: non-empty string, length 1-120
- `description`: non-empty string, length 1-500
- `required`: boolean

Common rules:

- additional unknown properties MUST be rejected
- if `required` is `true`, `default` MUST NOT be present
- if `required` is `false` and `fieldType` is not `file`, `default` MUST be present
- for non-`file` fields, `default` type MUST match the field type
- `null` values are not valid for any setting value or default

## 4. Supported Field Types

Allowed `fieldType` values:

- `text`
- `secret`
- `number`
- `slider`
- `switch`
- `checkbox`
- `file`
- `artifact-ref`
- `rubric-ref`

### 4.1 `text`

Allowed keys:

- common keys
- `default` (string, REQUIRED when `required=false`)
- `minLength` (integer, >= 0)
- `maxLength` (integer, >= 1)

Constraints:

- if both are present, `minLength <= maxLength`
- `default` length MUST satisfy min/max constraints

### 4.2 `secret`

Allowed keys:

- common keys
- `default` (string, REQUIRED when `required=false`)
- `minLength` (integer, >= 0)
- `maxLength` (integer, >= 1)

Constraints:

- if both are present, `minLength <= maxLength`
- `default` length MUST satisfy min/max constraints

### 4.3 `number`

Allowed keys:

- common keys
- `default` (number, REQUIRED when `required=false`)
- `minimum` (number)
- `maximum` (number)
- `step` (number, > 0)

Constraints:

- `minimum` and `maximum` are REQUIRED
- `minimum <= maximum`
- `default` MUST be within `[minimum, maximum]`
- if `step` is present, `(default - minimum) / step` MUST be an integer within floating-point tolerance

### 4.4 `slider`

Allowed keys:

- common keys
- `default` (number, REQUIRED when `required=false`)
- `minimum` (number, REQUIRED)
- `maximum` (number, REQUIRED)
- `step` (number, REQUIRED, > 0)
- `marks` (object, REQUIRED)

`marks` rules:

- keys MUST parse as numbers
- each key value MUST be a non-empty string label
- each numeric mark MUST be within `[minimum, maximum]`

Other constraints:

- `minimum <= maximum`
- `default` MUST be within `[minimum, maximum]`
- `(default - minimum) / step` MUST be an integer within floating-point tolerance

### 4.5 `switch`

Allowed keys:

- common keys
- `default` (boolean, REQUIRED when `required=false`)

### 4.6 `checkbox`

Allowed keys:

- common keys
- `default` (boolean, REQUIRED when `required=false`)

### 4.7 `file`

Allowed keys:

- common keys
- `allowedTypes` (array of non-empty strings, REQUIRED)

`file` rules:

- `default` MUST NOT be present
- `allowedTypes` entries MUST be unique

### 4.8 `artifact-ref`

Allowed keys:

- common keys
- `allowedTypes` (array of non-empty strings, REQUIRED)
- `default` (string, REQUIRED when `required=false`)

`artifact-ref` rules:

- `allowedTypes` entries MUST be unique
- `default` MUST be a valid artifact identifier string

### 4.9 `rubric-ref`

Allowed keys:

- common keys
- `default` (string, REQUIRED when `required=false`)

`rubric-ref` rules:

- `default` MUST be a valid rubric identifier string

## 5. Backend Contract

### 5.1 Plugin Descriptor

`PluginDescriptor.settings_schema` MUST accept:

- a plain `dict[str, Any]` (wire format)
- a `SettingsSchema` object (SDK format)

When serialized, API output MUST always emit plain JSON object format for `settings_schema`.

### 5.2 Registration-Time Validation

Registration MUST validate schema structure and constraints fully.
If invalid, registration MUST fail with `422 Unprocessable Entity`.
No partial acceptance is allowed.

### 5.3 Error Format for Registration

For invalid schemas, response body MUST be:

```json
{
  "detail": [
    {
      "type": "invalid_settings_schema",
      "plugin_id": "<plugin_id>",
      "message": "<human-readable reason>",
      "field_path": "<settingKey.property>"
    }
  ]
}
```

`field_path` MUST point to the exact failing property whenever possible.

## 6. Runtime Settings Validation and Hydration

Runtime settings validation is REQUIRED and always enabled.

At workflow execution:

1. platform resolves plugin and schema
2. incoming settings object is validated against schema
3. unknown setting keys are rejected
4. effective settings are built by applying defaults for all omitted optional fields
5. validated, hydrated settings are delivered to the extension payload

Error behavior:

- invalid client-provided settings: `400 Bad Request`
- corrupted stored schema or schema/runtime mismatch: `422 Unprocessable Entity`

### 6.1 Execution Error Payloads

For invalid values:

```json
{
  "detail": "Settings validation failed for plugin '<plugin_id>': field '<field>' <reason>"
}
```

For corrupted schema:

```json
{
  "detail": "Cannot execute workflow: plugin '<plugin_id>' has corrupted settings_schema"
}
```

## 7. Extension Webhook Payload Contract

Settings MUST be sent under `payload.params.settings`.
Payload structure MUST include `meta.plugin_id` and `meta.plugin_type`.

Canonical shape:

```json
{
  "job_id": "job_abc123",
  "payload": {
    "action": "plugin.grade.simple",
    "params": {
      "settings": {
        "model": "gpt-4.1",
        "temperature": 0.7,
        "includeSuggestions": true
      }
    },
    "meta": {
      "plugin_id": "fair.core.grader.simple",
      "plugin_type": "grader"
    }
  }
}
```

## 8. Frontend Requirements

### 8.1 Type System

Frontend MUST use a discriminated union keyed by `fieldType` and a shared base interface.
Component dispatch MUST be keyed directly by `fieldType`.
Legacy dispatch based on `title` MUST NOT be used.

### 8.2 Localization

All new or modified user-facing strings in plugin settings UI MUST be localized.
Hardcoded UI strings are not allowed.

Localization requirements:

- add/update translation keys in existing namespace for plugin settings
- update all supported locales in this repository: English and Spanish where applicable for shared UI strings
- keep schema-provided `label` and `description` as runtime content and do not translate them in platform code

## 9. SDK API Requirements

A typed settings module MUST exist at:

`src/fair_platform/extension_sdk/settings.py`

It MUST provide:

- base `SettingsField`
- concrete field models for each supported `fieldType`
- `SettingsSchema` model with `properties: dict[str, SettingsField]`
- builder methods on `SettingsSchema`:
  - `add(key: str, field: SettingsField) -> SettingsSchema`
  - `from_pairs(pairs: Iterable[tuple[str, SettingsField]]) -> SettingsSchema`
- serialization to normalized flat dict form with no `to_dict()` call requirement

`PluginDescriptor(settings_schema=SettingsSchema(...))` MUST work directly.
`SettingsSchema().add(...).add(...)` MUST work and be part of the supported public SDK API.

## 10. Migration Requirement

Core extension definitions MUST be migrated to the new schema contract and MUST pass `SettingsSchema` directly in `PluginDescriptor`.
Legacy wrapper schema (`title/type/properties`) MUST be removed from core extension plugins.

## 11. Required Test Coverage

### 11.1 Backend Unit Tests

Required tests:

- `SettingsSchema` serializes through `PluginDescriptor` without manual conversion
- unknown `fieldType` is rejected at registration
- `required=true` + `default` is rejected
- type-specific constraint violations are rejected
- unknown keys in field definitions are rejected

### 11.2 Backend Integration Tests

Required tests:

- valid plugin registration with flat schema succeeds (`200`)
- invalid schema returns `422` with structured `detail[]`
- execution with invalid settings returns `400`
- execution against corrupted schema returns `422`

### 11.3 Frontend Tests

Required tests:

- field rendering dispatches by `fieldType`
- invalid schema shows localized error state
- no hardcoded plugin-settings UI strings introduced by this change

## 12. Canonical Example

```python
from fair_platform.extension_sdk import FairExtension, PluginDescriptor
from fair_platform.extension_sdk.settings import (
    SettingsSchema,
    TextField,
    SliderField,
    SwitchField,
)

settings = (
    SettingsSchema()
    .add(
        "model",
        TextField(
            fieldType="text",
            label="Language Model",
            description="Model name used for grading.",
            required=False,
            default="gpt-4.1",
            minLength=1,
            maxLength=100,
        ),
    )
    .add(
        "temperature",
        SliderField(
            fieldType="slider",
            label="Creativity",
            description="Sampling temperature for response generation.",
            required=False,
            default=0.7,
            minimum=0,
            maximum=2,
            step=0.1,
            marks={"0": "Deterministic", "0.7": "Balanced", "2": "Creative"},
        ),
    )
    .add(
        "includeSuggestions",
        SwitchField(
            fieldType="switch",
            label="Include Suggestions",
            description="Include actionable suggestions in feedback.",
            required=False,
            default=True,
        ),
    )
)

plugin = PluginDescriptor(
    plugin_id="my.grader",
    extension_id="my-extension",
    plugin_type="grader",
    name="Custom Grader",
    action="grade",
    settings_schema=settings,
)

ext = FairExtension("my-extension", "http://platform:8000", "secret", plugins=[plugin])
```

## 13. Non-Goals

This specification does not define typed runtime binding such as `settings_model` generics. Transport format remains JSON settings map in webhook payload.

End of specification.

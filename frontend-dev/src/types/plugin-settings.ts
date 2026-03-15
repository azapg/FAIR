export type SettingsFieldType =
  | "text"
  | "secret"
  | "number"
  | "slider"
  | "switch"
  | "checkbox"
  | "file"
  | "artifact-ref"
  | "rubric-ref";

export interface SettingsFieldBase {
  fieldType: SettingsFieldType;
  label: string;
  description: string;
  required: boolean;
  default?: unknown;
}

export interface TextSettingsField extends SettingsFieldBase {
  fieldType: "text" | "secret";
  default?: string;
  minLength?: number;
  maxLength?: number;
}

export interface NumberSettingsField extends SettingsFieldBase {
  fieldType: "number";
  default?: number;
  minimum: number;
  maximum: number;
  step?: number;
}

export interface SliderSettingsField extends SettingsFieldBase {
  fieldType: "slider";
  default?: number;
  minimum: number;
  maximum: number;
  step: number;
  marks: Record<string, string>;
}

export interface BooleanSettingsField extends SettingsFieldBase {
  fieldType: "switch" | "checkbox";
  default?: boolean;
}

export interface FileSettingsField extends SettingsFieldBase {
  fieldType: "file";
  allowedTypes: string[];
}

export interface ArtifactRefSettingsField extends SettingsFieldBase {
  fieldType: "artifact-ref";
  allowedTypes: string[];
  default?: string;
}

export interface RubricRefSettingsField extends SettingsFieldBase {
  fieldType: "rubric-ref";
  default?: string;
}

export type PluginSettingsField =
  | TextSettingsField
  | NumberSettingsField
  | SliderSettingsField
  | BooleanSettingsField
  | FileSettingsField
  | ArtifactRefSettingsField
  | RubricRefSettingsField;

export type PluginSettingsSchema = Record<string, PluginSettingsField>;

export function normalizePluginSettingsSchema(input: unknown): PluginSettingsSchema {
  if (!input || typeof input !== "object") {
    return {};
  }

  const candidate = input as Record<string, unknown>;
  if (
    "properties" in candidate &&
    candidate.properties &&
    typeof candidate.properties === "object"
  ) {
    return candidate.properties as PluginSettingsSchema;
  }

  return candidate as PluginSettingsSchema;
}

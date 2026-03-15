import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RuntimePluginRead } from "@/hooks/use-plugins";
import { SDKArtifact, toSDKArtifact, useArtifacts } from "@/hooks/use-artifacts";
import { Rubric, useRubrics } from "@/hooks/use-rubrics";
import { useCallback, useRef } from "react";
import { useWorkflowStore } from "@/store/workflows-store";
import { shallow } from "zustand/shallow";
import { useTranslation } from "react-i18next";
import { ArtifactRefSettingsField, BooleanSettingsField, FileSettingsField, NumberSettingsField, PluginSettingsField, PluginSettingsSchema, RubricRefSettingsField, SliderSettingsField, TextSettingsField } from "@/types/plugin-settings";

interface PluginSettingsProps {
  plugin: RuntimePluginRead;
  values?: Record<string, unknown>;
  onChange?: (values: Record<string, unknown>) => void;
}

interface BaseInputProps<T extends PluginSettingsField = PluginSettingsField> {
  property: T;
  value: unknown;
  onChange: (value: unknown) => void;
  name: string;
}

function TextField({ property, value, onChange, name }: BaseInputProps<TextSettingsField>) {
  const textValue = typeof value === "string" ? value : "";
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{property.description}</p>
      <Textarea
        id={name}
        className="min-h-[80px] resize-y"
        placeholder={property.default?.toString() || ""}
        value={textValue}
        onChange={(e) => onChange(e.target.value)}
        minLength={property.minLength}
        maxLength={property.maxLength}
      />
    </div>
  );
}

function SensitiveTextField({ property, value, onChange, name }: BaseInputProps<TextSettingsField>) {
  const textValue = typeof value === "string" ? value : "";
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{property.description}</p>
      <Input
        id={name}
        type="password"
        placeholder={property.default?.toString() || ""}
        value={textValue}
        onChange={(e) => onChange(e.target.value)}
        minLength={property.minLength}
        maxLength={property.maxLength}
      />
    </div>
  );
}

function NumberField({ property, value, onChange, name }: BaseInputProps<NumberSettingsField>) {
  const { minimum: min, maximum: max, step } = property;
  const numberValue = typeof value === "number" ? value : "";

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{property.description}</p>
      <Input
        id={name}
        type="number"
        placeholder={property.default?.toString() || ""}
        value={numberValue}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
      />
    </div>
  );
}

function SwitchField({ property, value, onChange, name }: BaseInputProps<BooleanSettingsField>) {
  const checked =
    typeof value === "boolean"
      ? value
      : typeof property.default === "boolean"
        ? property.default
        : false;

  return (
    <div className="flex items-center justify-between space-y-2">
      <div className="space-y-0.5">
        <p className="text-xs text-muted-foreground">{property.description}</p>
      </div>
      <Switch
        id={name}
        checked={checked}
        onCheckedChange={onChange}
      />
    </div>
  );
}

function CheckboxField({ property, value, onChange, name }: BaseInputProps<BooleanSettingsField>) {
  const checked =
    typeof value === "boolean"
      ? value
      : typeof property.default === "boolean"
        ? property.default
        : false;

  return (
    <div className="flex items-center justify-between space-y-2">
      <div className="space-y-0.5">
        <p className="text-xs text-muted-foreground">{property.description}</p>
      </div>
      <Checkbox
        id={name}
        checked={checked}
        onCheckedChange={(checked) => onChange(checked === true)}
      />
    </div>
  );
}

function FileField({ property }: BaseInputProps<FileSettingsField>) {
  const { t } = useTranslation();
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{property.description}</p>
      <div className="border border-dashed border-muted-foreground/25 rounded-lg p-4 text-center">
        <p className="text-sm text-muted-foreground">
          {t("workflow.pluginSettings.fileUploadNotImplemented")}
        </p>
      </div>
    </div>
  );
}

function SliderField({ property, value, onChange, name }: BaseInputProps<SliderSettingsField>) {
  const { minimum: min, maximum: max, step } = property;
  const currentValue =
    typeof value === "number"
      ? value
      : typeof property.default === "number"
        ? property.default
        : min;

  const marks = property.marks
    ? Object.entries(property.marks).sort(
        ([a], [b]) => Number(a) - Number(b),
      )
    : [];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          {property.description}
        </p>
        <span className="text-xs tabular-nums text-muted-foreground">
          {currentValue}
        </span>
      </div>
      <div className="w-full">
        <Slider
          id={name}
          value={[currentValue]}
          min={min}
          max={max}
          step={step}
          onValueChange={(values) => onChange(values[0] ?? currentValue)}
          className="w-full"
        />
      </div>
      {marks.length > 0 && (
        <div className="w-full flex items-center justify-between gap-2 text-xs text-muted-foreground">
          {marks.map(([markValue, label]) => (
            <span key={markValue} className="min-w-0 truncate">
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CourseArtifactsSelectorField({
  property,
  value,
  onChange,
  name,
}: BaseInputProps<ArtifactRefSettingsField>) {
  const { t } = useTranslation();
  const activeCourseId = useWorkflowStore((state) => state.activeCourseId);
  const { data: artifacts = [], isLoading } = useArtifacts(
    activeCourseId ? { courseId: activeCourseId } : undefined,
    !!activeCourseId,
  );

  const allowedTypes = property.allowedTypes;
  const hasTypeFilter = Array.isArray(allowedTypes) && allowedTypes.length > 0;

  const normalized: SDKArtifact[] = artifacts
    .filter((artifact) => artifact.accessLevel === "assignment")
    .filter((artifact) =>
      hasTypeFilter ? allowedTypes.includes(artifact.mime) : true,
    )
    .map(toSDKArtifact);
  const selectedId = typeof value === "string" ? value : "";

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{property.description}</p>
      <Select
        value={selectedId}
        onValueChange={(artifactId) => onChange(artifactId)}
        disabled={!activeCourseId || isLoading || normalized.length === 0}
      >
        <SelectTrigger id={name} className="w-full" size="sm">
          <SelectValue
            placeholder={
              !activeCourseId
                ? t("workflow.pluginSettings.selectCourseFirst")
                : isLoading
                  ? t("workflow.pluginSettings.loadingArtifacts")
                  : normalized.length === 0
                    ? t("workflow.pluginSettings.noArtifacts")
                    : t("workflow.pluginSettings.selectArtifact")
            }
          />
        </SelectTrigger>
        <SelectContent
          position="popper"
          className="w-[--radix-select-trigger-width]"
        >
          {normalized.map((artifact) => (
            <SelectItem key={artifact.id} value={artifact.id}>
              {artifact.title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function RubricField({
  property,
  value,
  onChange,
  name,
}: BaseInputProps<RubricRefSettingsField>) {
  const { t } = useTranslation();
  const { data: rubrics = [], isLoading } = useRubrics();
  const selectedId = typeof value === "string" ? value : "";

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{property.description}</p>
      <Select
        value={selectedId}
        onValueChange={(rubricId) => onChange(rubricId)}
        disabled={isLoading || rubrics.length === 0}
      >
        <SelectTrigger id={name} className="w-full" size="sm">
          <SelectValue
            placeholder={
              isLoading
                ? t("workflow.pluginSettings.loadingRubrics")
                : rubrics.length === 0
                  ? t("workflow.pluginSettings.noRubrics")
                  : t("workflow.pluginSettings.selectRubric")
            }
          />
        </SelectTrigger>
        <SelectContent
          position="popper"
          className="w-[--radix-select-trigger-width]"
        >
          {rubrics.map((rubric: Rubric) => (
            <SelectItem key={rubric.id} value={rubric.id}>
              {rubric.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function UnsupportedField({
  property,
}: {
  property: Partial<PluginSettingsField> & { fieldType?: string };
  name: string;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium text-destructive">
        {t("workflow.pluginSettings.unsupportedField", {
          fieldType: property.fieldType || t("workflow.pluginSettings.unknownFieldType"),
        })}
      </Label>
    </div>
  );
}

const INPUT_COMPONENTS = {
  text: TextField,
  secret: SensitiveTextField,
  number: NumberField,
  slider: SliderField,
  "artifact-ref": CourseArtifactsSelectorField,
  "rubric-ref": RubricField,
  switch: SwitchField,
  checkbox: CheckboxField,
  file: FileField,
} as const;

type InputComponentKey = keyof typeof INPUT_COMPONENTS;

function getComponentType(
  property: PluginSettingsField,
): InputComponentKey | null {
  return property.fieldType in INPUT_COMPONENTS
    ? (property.fieldType as InputComponentKey)
    : null;
}

function toTitleCaseFromKey(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]/g, " ")
    .replace(/^\w/, (char) => char.toUpperCase());
}

function createInputComponent(
  property: PluginSettingsField,
  name: string,
  value: unknown,
  onChange: (value: unknown) => void,
) {
  const componentType = getComponentType(property);
  const label = property.label || toTitleCaseFromKey(name);

  if (!componentType) {
    return <UnsupportedField key={name} property={property} name={name} />;
  }

  const Component = INPUT_COMPONENTS[componentType];

  return (
    <div key={name} className="space-y-2">
      <Label htmlFor={name} className="text-sm font-medium">
        {label}
      </Label>
      <Component
        property={property}
        value={value}
        onChange={onChange}
        name={name}
      />
    </div>
  );
}

function isValidFieldShape(value: unknown): value is PluginSettingsField {
  return (
    !!value &&
    typeof value === "object" &&
    "fieldType" in value &&
    "label" in value &&
    "description" in value &&
    "required" in value
  );
}

export function PluginSettings({
  plugin,
  values = {},
  onChange,
}: PluginSettingsProps) {
  const { t } = useTranslation();
  const schema = plugin.settingsSchema as PluginSettingsSchema | undefined;
  const patchActivePluginSetting = useWorkflowStore(
    (state) => state.patchActivePluginSetting,
  );

  const pluginDraft = useWorkflowStore(
    useCallback(
      (state) =>
        state.drafts[state.activeWorkflowId || ""]?.plugins?.[plugin.type],
      [plugin.type],
    ),
    shallow,
  );

  const settings = pluginDraft?.settings ?? values ?? {};

  const handleFieldChange = useCallback(
    (key: string, value: unknown) => {
      const next = { ...(pluginDraft?.settings ?? values ?? {}), [key]: value };
      onChange?.(next);
      patchActivePluginSetting(plugin, key, value, values);
    },
    [plugin, pluginDraft?.settings, values, onChange, patchActivePluginSetting],
  );
  const handlersRef = useRef<Record<string, (v: unknown) => void>>({});
  const getHandler = useCallback(
    (key: string) => {
      if (!handlersRef.current[key]) {
        handlersRef.current[key] = (value: unknown) =>
          handleFieldChange(key, value);
      }
      return handlersRef.current[key];
    },
    [handleFieldChange],
  );

  if (!schema || Object.keys(schema).length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-muted-foreground">
          {t("workflow.pluginSettings.noSettings")}
        </p>
      </div>
    );
  }

  const entries = Object.entries(schema);
  const invalidSchema = entries.some(([, property]) => !isValidFieldShape(property));
  if (invalidSchema) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-destructive">
          {t("workflow.pluginSettings.invalidSchema")}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {entries.map(([key, property]) =>
          createInputComponent(
            property as PluginSettingsField,
            key,
            settings[key],
            getHandler(key),
          ),
        )}
      </div>
    </div>
  );
}

export type { PluginSettingsProps };

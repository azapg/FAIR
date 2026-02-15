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

interface PydanticProperty {
  type: "string" | "number" | "boolean" | "object";
  title: string;
  description?: string;
  default?: any;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  allowed_mime_types?: string[];
  allowedMimeTypes?: string[];
  $ref?: string;
  [key: string]: unknown;
}

interface PydanticSchema {
  properties: Record<string, PydanticProperty>;
  $defs?: Record<string, any>;
  title: string;
  type: "object";
}

interface PluginSettingsProps {
  plugin: RuntimePluginRead;
  values?: Record<string, any>;
  onChange?: (values: Record<string, any>) => void;
}

interface BaseInputProps {
  property: PydanticProperty;
  value: any;
  onChange: (value: any) => void;
  name: string;
}

function TextField({ property, value, onChange, name }: BaseInputProps) {
  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <Textarea
        id={name}
        className="min-h-[80px] resize-y"
        placeholder={property.default?.toString() || ""}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        minLength={property.minLength}
        maxLength={property.maxLength}
      />
    </div>
  );
}

function SensitiveTextField({ property, value, onChange, name }: BaseInputProps) {
  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <Input
        id={name}
        type="password"
        placeholder={property.default?.toString() || ""}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        minLength={property.minLength}
        maxLength={property.maxLength}
      />
    </div>
  );
}

function NumberField({ property, value, onChange, name }: BaseInputProps) {
  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <Input
        id={name}
        type="number"
        placeholder={property.default?.toString() || ""}
        value={value || ""}
        onChange={(e) => onChange(Number(e.target.value))}
        min={property.minimum}
        max={property.maximum}
        step={property.type === "number" ? "any" : "1"}
      />
    </div>
  );
}

function SwitchField({ property, value, onChange, name }: BaseInputProps) {
  return (
    <div className="flex items-center justify-between space-y-2">
      <div className="space-y-0.5">
        {property.description && (
          <p className="text-xs text-muted-foreground">
            {property.description}
          </p>
        )}
      </div>
      <Switch
        id={name}
        checked={value ?? property.default ?? false}
        onCheckedChange={onChange}
      />
    </div>
  );
}

function CheckboxField({ property, value, onChange, name }: BaseInputProps) {
  return (
    <div className="flex items-center justify-between space-y-2">
      <div className="space-y-0.5">
        {property.description && (
          <p className="text-xs text-muted-foreground">
            {property.description}
          </p>
        )}
      </div>
      <Checkbox
        id={name}
        checked={value ?? property.default ?? false}
        onCheckedChange={(checked) => onChange(checked === true)}
      />
    </div>
  );
}

function FileField({ property }: BaseInputProps) {
  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <div className="border border-dashed border-muted-foreground/25 rounded-lg p-4 text-center">
        <p className="text-sm text-muted-foreground">
          File upload not implemented
        </p>
      </div>
    </div>
  );
}

function SliderField({ property, value, onChange, name }: BaseInputProps) {
  const min = property.minimum ?? 0;
  const max = property.maximum ?? 100;
  const step = typeof property.step === "number" ? property.step : 1;
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
        {property.description ? (
          <p className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
            {property.description}
          </p>
        ) : (
          <span />
        )}
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
}: BaseInputProps) {
  const activeCourseId = useWorkflowStore((state) => state.activeCourseId);
  const { data: artifacts = [], isLoading } = useArtifacts(
    activeCourseId ? { courseId: activeCourseId } : undefined,
    !!activeCourseId,
  );

  const allowedMimeTypes =
    property.allowed_mime_types ?? property.allowedMimeTypes ?? [];
  const hasMimeFilter = Array.isArray(allowedMimeTypes) && allowedMimeTypes.length > 0;

  const normalized: SDKArtifact[] = artifacts
    .filter((artifact) => artifact.accessLevel === "assignment")
    .filter((artifact) =>
      hasMimeFilter ? allowedMimeTypes.includes(artifact.mime) : true,
    )
    .map(toSDKArtifact);
  const selectedId = typeof value?.id === "string" ? value.id : "";

  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <Select
        value={selectedId}
        onValueChange={(artifactId) => {
          const selected = normalized.find((item) => item.id === artifactId);
          if (selected) onChange(selected);
        }}
        disabled={!activeCourseId || isLoading || normalized.length === 0}
      >
        <SelectTrigger id={name} className="w-full" size="sm">
          <SelectValue
            placeholder={
              !activeCourseId
                ? "Select a course first"
                : isLoading
                  ? "Loading artifacts..."
                  : normalized.length === 0
                    ? "No course artifacts available"
                    : "Select an artifact"
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
}: BaseInputProps) {
  const { data: rubrics = [], isLoading } = useRubrics();
  const selectedId = typeof value?.id === "string" ? value.id : "";

  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <Select
        value={selectedId}
        onValueChange={(rubricId) => {
          const selected = rubrics.find((item: Rubric) => item.id === rubricId);
          if (selected) onChange(selected);
        }}
        disabled={isLoading || rubrics.length === 0}
      >
        <SelectTrigger id={name} className="w-full" size="sm">
          <SelectValue
            placeholder={
              isLoading
                ? "Loading rubrics..."
                : rubrics.length === 0
                  ? "No rubrics available"
                  : "Select a rubric"
            }
          />
        </SelectTrigger>
        <SelectContent
          position="popper"
          className="w-[--radix-select-trigger-width]"
        >
          {rubrics.map((rubric) => (
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
  property: PydanticProperty;
  name: string;
}) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium text-destructive">
        Unsupported field: {property.title}
      </Label>
      <p className="text-xs text-muted-foreground">
        Type: {property.type} | Title: {property.title}
      </p>
    </div>
  );
}

// Component factory
const INPUT_COMPONENTS = {
  TextField,
  SensitiveTextField,
  NumberField,
  SliderField,
  CourseArtifactsSelectorField,
  RubricField,
  SwitchField,
  CheckboxField,
  FileField,
} as const;

type InputComponentKey = keyof typeof INPUT_COMPONENTS;

function getComponentType(
  property: PydanticProperty,
): InputComponentKey | null {
  if (property.title in INPUT_COMPONENTS) {
    return property.title as InputComponentKey;
  }

  return null;
}

function createInputComponent(
  property: PydanticProperty,
  name: string,
  value: any,
  onChange: (value: any) => void,
) {
  const componentType = getComponentType(property);

  if (!componentType) {
    return <UnsupportedField key={name} property={property} name={name} />;
  }

  const Component = INPUT_COMPONENTS[componentType];

  return (
    <Component
      key={name}
      property={property}
      value={value}
      onChange={onChange}
      name={name}
    />
  );
}

export function PluginSettings({
  plugin,
  values = {},
  onChange,
}: PluginSettingsProps) {
  const schema = plugin.settingsSchema;
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

  // TODO: All this mess to avoid re-creating handlers on every render,
  //  but I am not sure if it's worth it. For now, I even't haven't seen results
  //  we will see if it stays after fixing parent re-renders.
  const handleFieldChange = useCallback(
    (key: string, value: any) => {
      const next = { ...(pluginDraft?.settings ?? values ?? {}), [key]: value };
      onChange?.(next);
      patchActivePluginSetting(plugin, key, value, values);
    },
    [plugin, pluginDraft?.settings, values, onChange, patchActivePluginSetting],
  );
  const handlersRef = useRef<Record<string, (v: any) => void>>({});
  const getHandler = useCallback(
    (key: string) => {
      if (!handlersRef.current[key]) {
        handlersRef.current[key] = (value: any) =>
          handleFieldChange(key, value);
      }
      return handlersRef.current[key];
    },
    [handleFieldChange],
  );

  if (!schema?.properties) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-muted-foreground">No settings available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {Object.entries(schema.properties).map(([key, property]) =>
          createInputComponent(property, key, settings[key], getHandler(key)),
        )}
      </div>
    </div>
  );
}

export type { PydanticSchema, PydanticProperty, PluginSettingsProps };

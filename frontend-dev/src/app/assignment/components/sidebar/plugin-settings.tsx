import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { RuntimePluginRead } from "@/hooks/use-plugins"
import {useCallback, useRef} from "react"
import { useWorkflowStore } from "@/store/workflows-store"
import { shallow } from "zustand/shallow"

interface PydanticProperty {
  type: 'string' | 'number' | 'boolean' | 'object'
  title: string
  description?: string
  default?: any
  minimum?: number
  maximum?: number
  minLength?: number
  maxLength?: number
  $ref?: string
}

interface PydanticSchema {
  properties: Record<string, PydanticProperty>
  $defs?: Record<string, any>
  title: string
  type: 'object'
}

interface PluginSettingsProps {
  plugin: RuntimePluginRead,
  values?: Record<string, any>
  onChange?: (values: Record<string, any>) => void
}

interface BaseInputProps {
  property: PydanticProperty
  value: any
  onChange: (value: any) => void
  name: string
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
        placeholder={property.default?.toString() || ''}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        minLength={property.minLength}
        maxLength={property.maxLength}
      />
    </div>
  )
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
        placeholder={property.default?.toString() || ''}
        value={value || ''}
        onChange={(e) => onChange(Number(e.target.value))}
        min={property.minimum}
        max={property.maximum}
        step={property.type === 'number' ? 'any' : '1'}
      />
    </div>
  )
}

function SwitchField({ property, value, onChange, name }: BaseInputProps) {
  return (
    <div className="flex items-center justify-between space-y-2">
      <div className="space-y-0.5">
        {property.description && (
          <p className="text-xs text-muted-foreground">{property.description}</p>
        )}
      </div>
      <Switch
        id={name}
        checked={value ?? property.default ?? false}
        onCheckedChange={onChange}
      />
    </div>
  )
}

function FileField({ property }: BaseInputProps) {
  return (
    <div className="space-y-2">
      {property.description && (
        <p className="text-xs text-muted-foreground">{property.description}</p>
      )}
      <div className="border border-dashed border-muted-foreground/25 rounded-lg p-4 text-center">
        <p className="text-sm text-muted-foreground">File upload not implemented</p>
      </div>
    </div>
  )
}

function UnsupportedField({ property }: { property: PydanticProperty; name: string }) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium text-destructive">
        Unsupported field: {property.title}
      </Label>
      <p className="text-xs text-muted-foreground">
        Type: {property.type} | Title: {property.title}
      </p>
    </div>
  )
}

// Component factory
const INPUT_COMPONENTS = {
  TextField,
  NumberField,
  SwitchField,
  FileField,
} as const

type InputComponentKey = keyof typeof INPUT_COMPONENTS

function getComponentType(property: PydanticProperty): InputComponentKey | null {
  if (property.title in INPUT_COMPONENTS) {
    return property.title as InputComponentKey
  }

  return null
}

function createInputComponent(
  property: PydanticProperty,
  name: string,
  value: any,
  onChange: (value: any) => void
) {
  const componentType = getComponentType(property)
  
  if (!componentType) {
    return <UnsupportedField key={name} property={property} name={name} />
  }
  
  const Component = INPUT_COMPONENTS[componentType]
  
  return (
    <Component
      key={name}
      property={property}
      value={value}
      onChange={onChange}
      name={name}
    />
  )
}

export function PluginSettings({ plugin, values = {}, onChange }: PluginSettingsProps) {
  const schema = plugin.settingsSchema
  const patchActivePluginSetting = useWorkflowStore(state => state.patchActivePluginSetting)

  const pluginDraft = useWorkflowStore(
    useCallback(
      (state) => state.drafts[state.activeWorkflowId || ""]?.plugins?.[plugin.type],
      [plugin.type]
    ),
    shallow
  )

  const settings = pluginDraft?.settings ?? values ?? {}

  // TODO: All this mess to avoid re-creating handlers on every render,
  //  but I am not sure if it's worth it. For now, I even't haven't seen results
  //  we will see if it stays after fixing parent re-renders.
  const handleFieldChange = useCallback((key: string, value: any) => {
    const next = { ...(pluginDraft?.settings ?? values ?? {}), [key]: value }
    onChange?.(next)
    patchActivePluginSetting(plugin, key, value, values)
  }, [plugin, pluginDraft?.settings, values, onChange, patchActivePluginSetting])
  const handlersRef = useRef<Record<string, (v: any) => void>>({})
  const getHandler = useCallback((key: string) => {
    if (!handlersRef.current[key]) {
      handlersRef.current[key] = (value: any) => handleFieldChange(key, value)
    }
    return handlersRef.current[key]
  }, [handleFieldChange])


  if (!schema?.properties) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-muted-foreground">No settings available</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {Object.entries(schema.properties).map(([key, property]) =>
          createInputComponent(
            property,
            key,
            settings[key],
            getHandler(key)
          )
        )}
      </div>
    </div>
  )
}

export type { PydanticSchema, PydanticProperty, PluginSettingsProps }

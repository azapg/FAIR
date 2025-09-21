import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

type SettingModel = {
    default?: any
    description?: string
    title: string
    type: string
    [key: string]: any
}

type SettingsModel = {
    properties?: Record<string, SettingModel>
}

function TextField({ setting, value, onChange }: { 
    setting: SettingModel
    value: any
    onChange: (value: any) => void 
}) {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground mb-1">{setting.description}</label>
        <Textarea
          className="w-full rounded px-3 py-2 text-sm resize-y min-h-[48px] bg-background"
          placeholder={setting.default}
        />
      </div>
    )
}

function Selector({ setting, value, onChange }: {
    setting: SettingModel
    value: any
    onChange: (value: any) => void
}) {
    const currentValue = value || setting.default || ''
    
    return (
        <div className="space-y-2">
            <Label>{setting.description || setting.title}</Label>
            <Select value={currentValue} onValueChange={onChange}>
                <SelectTrigger>
                    <SelectValue placeholder={setting.description} />
                </SelectTrigger>
                <SelectContent>
                    {setting.options?.map((option, index) => (
                        <SelectItem key={index} value={option.value}>
                            {option.label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    )
}

// Factory function
const InputFactory = {
    TextField,
    Selector
} as const

function createInput(setting: SettingModel, key: string, value: any, onChange: (value: any) => void) {
    const Component = InputFactory[setting.title as keyof typeof InputFactory]
    
    if (!Component) {
        return (
            <div key={key} className="space-y-2">
                <Label>Unsupported input type: {setting.title}</Label>
            </div>
        )
    }
    
    return <Component key={key} setting={setting} value={value} onChange={onChange} />
}

export function PluginSettings({ properties }: SettingsModel) {
    // You'll want to manage state here for form values
    const handleChange = (key: string, value: any) => {
        // TODO: Implement state management
        console.log(`${key}: ${value}`)
    }

    return (
        <div className="space-y-4">
            {properties ? Object.entries(properties).map(([key, setting]) => 
                createInput(setting, key, undefined, (value) => handleChange(key, value))
            ) : null}
        </div>
    )
}

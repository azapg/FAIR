import { PluginSettingsSchema } from "@/types/plugin-settings";

export function extractDefaults(schema: PluginSettingsSchema): Record<string, any> {
  return Object.entries(schema).reduce((acc, [key, property]) => {
    if (property.default !== undefined) {
      acc[key] = property.default;
    }
    return acc;
  }, {} as Record<string, any>);
}

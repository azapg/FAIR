import {PydanticSchema} from "@/app/assignment/components/sidebar/plugin-settings";

export function extractDefaults(schema: PydanticSchema): Record<string, any> {
  return Object.entries(schema.properties).reduce((acc, [key, property]) => {
    if (property.default !== undefined) {
      acc[key] = property.default
    }
    return acc
  }, {} as Record<string, any>)
}
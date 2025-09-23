import { useState } from "react"
import SectionContainer from "./section-container"
import { Button } from "@/components/ui/button"
import {usePlugins} from "@/hooks/use-plugins";
import {PluginSettings, PydanticSchema} from "@/app/assignment/components/plugin-settings";
import {Select, SelectTrigger, SelectItem, SelectContent, SelectValue} from "@/components/ui/select"

export default function ValidatorSection() {
  let {data: plugins = [], isLoading, isError} = usePlugins("validation");
  const [settings, setSettings] = useState<PydanticSchema | null>(null);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (isError) {
    return <div>Error loading plugins</div>;
  }

  const onSelectPluginChange = (pluginName: string) => {
    const plugin = plugins.find((p) => p.name === pluginName);
    if (plugin) {
      setSettings(plugin.settings as any);
    } else {
      setSettings(null);
    }
  }

  return (
    <SectionContainer title="Validator">
      <Select onValueChange={onSelectPluginChange}>
        <SelectTrigger className="w-full" size={"sm"}>
          <SelectValue placeholder="Select plugin"/>
        </SelectTrigger>
        <SelectContent position="popper" className="w-[--radix-select-trigger-width]">
          {plugins?.map((option) => (
            <SelectItem key={option.id} value={option.name}>
              {option.name}
            </SelectItem>
          ))}
          <SelectItem value={undefined!}>None</SelectItem>
        </SelectContent>
      </Select>

      {settings && <PluginSettings type="validation" schema={settings}/>}
      <Button variant={"secondary"}>Validate all</Button>
    </SectionContainer>
  )
}

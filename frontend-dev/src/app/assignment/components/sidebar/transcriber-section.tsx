"use client"
import SectionContainer from "@/app/assignment/components/sidebar/section-container"
import {Button} from "@/components/ui/button"
import {usePlugins} from "@/hooks/use-plugins";
import {useState} from "react";
import {PluginSettings, PydanticSchema} from "@/app/assignment/components/sidebar/plugin-settings";
import {Select, SelectTrigger, SelectItem, SelectContent, SelectValue} from "@/components/ui/select"

export default function TranscriberSection() {
  let {data: plugins = [], isLoading, isError} = usePlugins("transcriber");
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
      // TODO: I should probably separate schema and settings in the backend
      setSettings(plugin.settings as any);
    } else {
      setSettings(null);
    }
  }

  return (
    <SectionContainer title="Transcriber">
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

      {settings && <PluginSettings type="transcriber" schema={settings}/>}
      <Button variant={"secondary"}>Transcribe all</Button>
    </SectionContainer>
  )
}


"use client"
import SectionContainer from "@/app/assignment/components/section-container"
import { Button } from "@/components/ui/button"
import { usePlugins } from "@/hooks/use-plugins";
import { useState } from "react";
import { PluginSettings } from "@/app/assignment/components/plugin-settings";

export default function TranscriberSection() {
  let { data: plugins = [], isLoading, isError } = usePlugins("transcription");
  const [plugin, setPlugin] = useState<string | null>(null);
  const [settings, setSettings] = useState<Record<string, any> | null>(null);

  const onSelectPluginChange = (plugin: string) => {
    console.log("Selected plugin:", plugin);
    console.log("Available plugins:", plugins);
    console.log("Found plugin:", plugins.find(p => p.name === plugin));
    setPlugin(plugins.find(p => p.name === plugin)?.id || null);
    setSettings(plugins.find(p => p.name === plugin)?.settings || null);
  }

  return (
    <SectionContainer pluginOptions={plugins?.map(plugin => plugin.name)} onSelectPluginChange={onSelectPluginChange}>
      <PluginSettings properties={settings?.properties}/>
      {/* <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground flex-1">Force Language</label>
        <Select defaultValue="auto">
          <SelectTrigger className="flex-1" size={"sm"}>
            <SelectValue placeholder="auto" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">auto</SelectItem>
            <SelectItem value="en">English</SelectItem>
            <SelectItem value="es">Spanish</SelectItem>
            <SelectItem value="fr">French</SelectItem>
            <SelectItem value="de">German</SelectItem>
            <SelectItem value="zh">Chinese</SelectItem>
            <SelectItem value="ar">Arabic</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-1 items-center text-xs">
        <label className="text-muted-foreground w-1/3 flex-1">Max tokens</label>
        <Input className={"flex-1"} type={"number"} max={10000} min={256} defaultValue={2048}/>
      </div> */}
      <Button variant={"secondary"}>Transcribe all</Button>
    </SectionContainer>
  )
}


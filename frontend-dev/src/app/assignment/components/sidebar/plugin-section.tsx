import { PluginType, useWorkflowStore } from "@/store/workflows-store";
import { PropsWithChildren, useEffect, useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PluginSettings } from "@/app/assignment/components/sidebar/plugin-settings";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SidebarGroup, SidebarGroupContent, SidebarGroupLabel } from "@/components/ui/sidebar";
import { Plus } from "lucide-react";

type PluginSectionProps = {
  title: string;
  action: string;
  type: PluginType;
}

export default function PluginSection({ title, action, type }: PluginSectionProps) {
  const {
    availablePlugins,
    draft,
    selectPlugin,
    updatePluginSettings,
    loadAvailablePlugins,
    isLoading
  } = useWorkflowStore();

  const [selectedPluginId, setSelectedPluginId] = useState<string>("");
  
  const plugins = availablePlugins[type] || [];
  const currentPluginConfig = draft.plugin_configs[type];
  const selectedPlugin = plugins.find(p => p.id === selectedPluginId);

  // Load plugins for this type if not already loaded
  useEffect(() => {
    if (plugins.length === 0 && !isLoading) {
      loadAvailablePlugins(type);
    }
  }, [type, plugins.length, isLoading, loadAvailablePlugins]);

  // Update selected plugin when draft changes
  useEffect(() => {
    if (currentPluginConfig && currentPluginConfig.plugin_id !== selectedPluginId) {
      setSelectedPluginId(currentPluginConfig.plugin_id);
    }
  }, [currentPluginConfig, selectedPluginId]);

  const onSelectPluginChange = (pluginId: string) => {
    setSelectedPluginId(pluginId);
    const plugin = plugins.find(p => p.id === pluginId);
    if (plugin) {
      selectPlugin(type, pluginId, plugin.hash);
    }
  };

  const onSettingsChange = (settings: Record<string, any>) => {
    updatePluginSettings(type, settings);
  };

  if (isLoading && plugins.length === 0) {
    return (
      <SectionContainer title={title}>
        <div className="text-muted-foreground text-sm">Loading plugins...</div>
      </SectionContainer>
    );
  }

  return (
    <SectionContainer title={title}>
      <div className="space-y-4">
        {/* Plugin Selection */}
        <Select onValueChange={onSelectPluginChange} value={selectedPluginId}>
          <SelectTrigger className="w-full" size={"sm"}>
            <SelectValue placeholder="Select plugin" />
          </SelectTrigger>
          <SelectContent position="popper" className="w-[--radix-select-trigger-width]">
            {plugins.map((plugin) => (
              <SelectItem key={plugin.id} value={plugin.id}>
                <div className="flex flex-col">
                  <span>{plugin.name}</span>
                  <span className="text-xs text-muted-foreground">
                    v{plugin.version} by {plugin.author}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Plugin Settings */}
        {selectedPlugin && currentPluginConfig && (
          <PluginSettings
            type={type}
            schema={selectedPlugin.settings_schema}
            values={currentPluginConfig.settings}
            onChange={onSettingsChange}
          />
        )}

        {/* Individual Plugin Action Button */}
        <Button 
          variant="secondary" 
          disabled={!selectedPlugin}
          className="w-full"
        >
          {action}
        </Button>
      </div>
    </SectionContainer>
  );
}

type SectionContainerProps = PropsWithChildren<{
  title: string
  defaultOpen?: boolean
  className?: string
}>

function SectionContainer({ title, defaultOpen = true, className, children }: SectionContainerProps) {
  return (
    <Collapsible defaultOpen={defaultOpen} className="group/collapsible">
      <SidebarGroup className={`group/section ${className ?? ""}`}>
        <SidebarGroupLabel>
          <SectionTrigger title={title} />
        </SidebarGroupLabel>
        <CollapsibleContent>
          <SidebarGroupContent className="flex flex-col pt-2 px-2 gap-4">
            {children}
          </SidebarGroupContent>
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  )
}

type SectionTriggerProps = {
  title: string
  className?: string
  iconSize?: number
}

function SectionTrigger({ title, className, iconSize = 12 }: SectionTriggerProps) {
  return (
    <CollapsibleTrigger
      className={`group/trigger flex w-full justify-between items-center text-base text-foreground cursor-pointer ${className ?? ""}`}
    >
      <span>{title}</span>
      <span className="relative inline-flex w-4 h-4 shrink-0 items-center justify-center">
        <Plus
          size={iconSize}
          className="
            origin-center transition-all duration-200
            group-data-[state=closed]/collapsible:rotate-0 group-data-[state=open]/collapsible:rotate-45
          "
        />
      </span>
    </CollapsibleTrigger>
  )
}
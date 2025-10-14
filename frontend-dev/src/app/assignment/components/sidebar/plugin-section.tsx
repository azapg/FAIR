import {PluginType, usePlugins, RuntimePluginRead} from "@/hooks/use-plugins";
import {PropsWithChildren, useEffect, useState} from "react";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {PluginSettings} from "@/app/assignment/components/sidebar/plugin-settings";
import {Button} from "@/components/ui/button";
import {Collapsible, CollapsibleContent, CollapsibleTrigger} from "@/components/ui/collapsible";
import {SidebarGroup, SidebarGroupContent, SidebarGroupLabel} from "@/components/ui/sidebar";
import {Plus} from "lucide-react";
import {useWorkflowStore} from "@/store/workflows-store";

type PluginSectionProps = {
  title: string;
  action: string;
  type: PluginType;
}

export default function PluginSection({title, action, type}: PluginSectionProps) {
  const {data: plugins = [], isLoading, isError} = usePlugins(type);
  const [selectedPlugin, setSelectedPlugin] = useState<RuntimePluginRead | null>(null);
  const saveDraft = useWorkflowStore(state => state.saveDraft);
  const activeCourseId = useWorkflowStore(state => state.activeCourseId);
  const currentDraft = useWorkflowStore(
    s => (s.activeWorkflowId ? s.drafts[s.activeWorkflowId] : undefined)
  );


  useEffect(() => {
    const pluginInDraft = currentDraft?.plugins[type];
    if (pluginInDraft) {
      const plugin = plugins.find((p) => p.id === pluginInDraft.id && p.hash === pluginInDraft.hash);
      if (plugin) {
        setSelectedPlugin(plugin);
      } else {
        setSelectedPlugin(null);
      }
    } else {
      setSelectedPlugin(null);
    }
  }, [currentDraft, plugins]);


  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (isError) {
    return <div>Error loading plugins</div>;
  }

  const runStep = () => {
    console.log({currentDraft});
  }

  const onSelectPluginChange = (id: string) => {
    const plugin = plugins.find((p) => p.id === id);
    if (plugin) {
      setSelectedPlugin(plugin);
      saveDraft({
        workflowId: currentDraft?.workflowId || crypto.randomUUID(),
        name: currentDraft?.name || 'Default Workflow',
        courseId: activeCourseId || '',
        ...currentDraft,
        plugins: {
          ...(currentDraft?.plugins || {}),
          [type]: {
            id: plugin.id,
            version: plugin.version,
            hash: plugin.hash,
            settings: {},
            settings_schema: plugin.settingsSchema
          }
        }
      });
    } else {
      setSelectedPlugin(null);
    }
  }

  return (
    <SectionContainer title={title}>
      <Select onValueChange={onSelectPluginChange} value={selectedPlugin?.id || ''}>
        <SelectTrigger className="w-full" size={"sm"}>
          <SelectValue placeholder="Select plugin" />
        </SelectTrigger>
        <SelectContent position="popper" className="w-[--radix-select-trigger-width]">
          {plugins?.map((option) => (
            <SelectItem key={option.id} value={option.id}>
              {option.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {selectedPlugin && currentDraft && <PluginSettings
          key={`${type}-settings-${selectedPlugin.id}-${selectedPlugin.hash}`}
          plugin={selectedPlugin}
          values={currentDraft.plugins[type]?.settings}
      />}
      <Button variant={"secondary"} onClick={runStep}>{action}</Button>
    </SectionContainer>
  )
}

type SectionContainerProps = PropsWithChildren<{
  title: string
  defaultOpen?: boolean
  className?: string
}>

function SectionContainer({title, defaultOpen = true, className, children}: SectionContainerProps) {
  return (
    <Collapsible defaultOpen={defaultOpen} className="group/collapsible">
      <SidebarGroup className={`group/section ${className ?? ""}`}>
        <SidebarGroupLabel>
          <SectionTrigger title={title}/>
        </SidebarGroupLabel>
        <CollapsibleContent>
          <SidebarGroupContent className="flex flex-col pt-2 px-2 gap-6">
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
import api from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { toCamelCase } from "@/lib/casing";
import { PluginSettingsSchema } from "@/types/plugin-settings";

export type Plugin = {
  id: string;
  name: string;
  author?: string;
  authorEmail?: string | null;
  description?: string | null;
  version?: string | null;
  source: string;
  type: PluginType;
};

export type ExtensionPlugin = Plugin & {
  settingsSchema: PluginSettingsSchema;
  settings: Record<string, any>;
};

export type ExtensionPluginRead = Omit<ExtensionPlugin, "settings">;

export type PluginType = "transcriber" | "grader" | "reviewer";

export const pluginsKeys = {
  all: ["plugins"] as const,
  lists: () => [...pluginsKeys.all, "list"] as const,
  list: () => [...pluginsKeys.lists()] as const,
  details: () => [...pluginsKeys.all, "detail"] as const,
  detail: (id: string) => [...pluginsKeys.details(), id] as const,
};

const fetchPlugins = async (
  type?: PluginType,
): Promise<ExtensionPluginRead[]> => {
  const params = type ? { type_filter: type } : {};
  const res = await api.get("/plugins", { params });
  const data = toCamelCase(res.data) as ExtensionPluginRead[];
  data.forEach((plugin) => {
    plugin.settingsSchema = plugin.settingsSchema ?? {};
  });

  return data;
};
const fetchPlugin = async (id: string): Promise<ExtensionPluginRead> => {
  const res = await api.get(`/plugins/${id}`);
  const plugin = toCamelCase(res.data) as ExtensionPluginRead;
  plugin.settingsSchema = plugin.settingsSchema ?? {};
  return plugin;
};

export const usePlugins = (type?: PluginType) => {
  return useQuery({
    queryKey: [...pluginsKeys.list(), type],
    queryFn: () => fetchPlugins(type),
  });
};

export const usePlugin = (id: string) => {
  return useQuery({
    queryKey: pluginsKeys.detail(id),
    queryFn: () => fetchPlugin(id),
    enabled: !!id,
  });
};

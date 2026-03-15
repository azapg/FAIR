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
  hash: string;
  source: string;
  type: PluginType;
};

export type RuntimePlugin = Plugin & {
  settingsSchema: PluginSettingsSchema;
  settings: Record<string, any>;
};

export type RuntimePluginRead = Omit<RuntimePlugin, "settings">;

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
): Promise<RuntimePluginRead[]> => {
  const params = type ? { type_filter: type } : {};
  const res = await api.get("/plugins", { params });
  const data = toCamelCase(res.data) as RuntimePluginRead[];
  data.forEach((plugin) => {
    plugin.settingsSchema = plugin.settingsSchema ?? {};
  });

  return data;
};
const fetchPlugin = async (id: string): Promise<RuntimePluginRead> => {
  const res = await api.get(`/plugins/${id}`);
  const plugin = toCamelCase(res.data) as RuntimePluginRead;
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

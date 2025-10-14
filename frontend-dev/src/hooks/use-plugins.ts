import api from "@/lib/api"
import { useQuery } from "@tanstack/react-query"
import {PydanticSchema} from "@/app/assignment/components/sidebar/plugin-settings";

export type Plugin = {
    id: string
    name: string
    author: string
    author_email?: string | null
    description?: string | null
    version: string
    hash: string
    source: string
    type: PluginType
}

export type RuntimePlugin = Plugin & {
  settingsSchema: PydanticSchema
  settings: Record<string, any>
}

export type RuntimePluginRead = Omit<RuntimePlugin, 'settings'>


export type PluginType = "transcriber" | "grader" | "validator"

export const pluginsKeys = {
    all: ['plugins'] as const,
    lists: () => [...pluginsKeys.all, 'list'] as const,
    list: () => [...pluginsKeys.lists()] as const,
    details: () => [...pluginsKeys.all, 'detail'] as const,
    detail: (id: string) => [...pluginsKeys.details(), id] as const,
}


const fetchPlugins = async (type?: PluginType): Promise<RuntimePluginRead[]> => {
    const params = type ? { type_filter: type } : {}
    const res = await api.get('/plugins', { params })
    return res.data
}
const fetchPlugin = async (id: string): Promise<RuntimePluginRead> => {
    const res = await api.get(`/plugins/${id}`)
    return res.data
}

export const usePlugins = (type?: PluginType) => {
    return useQuery({
        queryKey: [...pluginsKeys.list(), type],
        queryFn: () => fetchPlugins(type),
    })
}

export const usePlugin = (id: string) => {
    return useQuery({
        queryKey: pluginsKeys.detail(id),
        queryFn: () => fetchPlugin(id),
        enabled: !!id,
    })
}


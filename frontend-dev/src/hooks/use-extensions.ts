import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import api from "@/lib/api";

export type ExtensionClient = {
  extensionId: string;
  scopes: string[];
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type ExtensionClientSecret = {
  extensionId: string;
  extensionSecret: string;
  scopes: string[];
  enabled: boolean;
};

export type CreateExtensionInput = {
  extensionId: string;
  scopes?: string[];
  enabled?: boolean;
};

export type UpdateExtensionInput = {
  extensionId: string;
  scopes: string[];
  enabled: boolean;
};

export const extensionKeys = {
  all: ["extensions"] as const,
  lists: () => [...extensionKeys.all, "list"] as const,
  list: () => [...extensionKeys.lists()] as const,
  details: () => [...extensionKeys.all, "detail"] as const,
  detail: (extensionId: string) => [...extensionKeys.details(), extensionId] as const,
};

const listExtensions = async (): Promise<ExtensionClient[]> => {
  const res = await api.get("/extensions/admin/clients");
  return res.data;
};

const getExtension = async (extensionId: string): Promise<ExtensionClient> => {
  const res = await api.get(`/extensions/admin/clients/${extensionId}`);
  return res.data;
};

const createExtension = async (payload: CreateExtensionInput): Promise<ExtensionClientSecret> => {
  const res = await api.post("/extensions/admin/clients", payload);
  return res.data;
};

const updateExtension = async (payload: UpdateExtensionInput): Promise<ExtensionClient> => {
  const res = await api.patch(`/extensions/admin/clients/${payload.extensionId}`, {
    scopes: payload.scopes,
    enabled: payload.enabled,
  });
  return res.data;
};

const rotateExtensionSecret = async (extensionId: string): Promise<ExtensionClientSecret> => {
  const res = await api.post(`/extensions/admin/clients/${extensionId}/rotate`);
  return res.data;
};

export function useExtensions(enabled = true) {
  return useQuery({
    queryKey: extensionKeys.list(),
    queryFn: listExtensions,
    enabled,
  });
}

export function useExtension(extensionId?: string, enabled = true) {
  return useQuery({
    queryKey: extensionId ? extensionKeys.detail(extensionId) : extensionKeys.detail("unknown"),
    queryFn: () => getExtension(extensionId as string),
    enabled: enabled && !!extensionId,
  });
}

export function useCreateExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createExtension,
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: extensionKeys.lists() });
      qc.invalidateQueries({ queryKey: extensionKeys.detail(created.extensionId) });
      toast.success("Extension created");
    },
    onError: (error: Error) => {
      toast.error("Failed to create extension", {
        description: error.message || "Something went wrong",
      });
    },
  });
}

export function useUpdateExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: updateExtension,
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: extensionKeys.lists() });
      qc.invalidateQueries({ queryKey: extensionKeys.detail(updated.extensionId) });
      toast.success("Extension permissions updated");
    },
    onError: (error: Error) => {
      toast.error("Failed to update extension permissions", {
        description: error.message || "Something went wrong",
      });
    },
  });
}

export function useRotateExtensionSecret() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: rotateExtensionSecret,
    onSuccess: (rotated) => {
      qc.invalidateQueries({ queryKey: extensionKeys.lists() });
      qc.invalidateQueries({ queryKey: extensionKeys.detail(rotated.extensionId) });
      toast.success("Extension secret reset");
    },
    onError: (error: Error) => {
      toast.error("Failed to reset extension secret", {
        description: error.message || "Something went wrong",
      });
    },
  });
}

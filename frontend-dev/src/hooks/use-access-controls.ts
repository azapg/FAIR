import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import api from "@/lib/api";

export type PlatformPolicy = {
  storedAdmissionMode: "open" | "allowlist" | "invite_only";
  effectiveAdmissionMode: "open" | "allowlist" | "invite_only";
  admissionSource: "database" | "environment";
  admissionLocked: boolean;
  storedAiControlsEnabled: boolean;
  effectiveAiControlsEnabled: boolean;
  aiControlsSource: "database" | "environment";
  aiControlsLocked: boolean;
};

export type AdmissionRule = {
  id: string;
  kind: "email" | "domain";
  value: string;
  createdAt: string;
};

export type RegistrationInvite = {
  id: string;
  email: string;
  expiresAt: string;
  redeemedAt: string | null;
  revokedAt: string | null;
  createdAt: string;
  active: boolean;
};

export type InviteSecret = RegistrationInvite & {
  token: string;
  registrationUrl: string;
};

export type CapabilityCostPolicy = {
  capabilityDefinitionId: string;
  capabilityId: string;
  displayName: string | null;
  version: string;
  surface: string;
  extensionId: string;
  classification: "unclassified" | "unmetered" | "ai";
  costUnits: number | null;
};

export type AIEntitlement = {
  userId: string;
  userName: string;
  userEmail: string;
  state: "disabled" | "limited" | "unlimited";
  monthlyLimitUnits: number | null;
  usedUnits: number;
  remainingUnits: number | null;
  periodStart: string;
  nextResetAt: string;
  controlsEnabled: boolean;
};

export type AIUsage = {
  periodStart: string;
  totalUnits: number;
  charges: Array<{
    id: string;
    executionId: string;
    userEmail: string;
    capabilityId: string;
    units: number;
    createdAt: string;
  }>;
};

const keys = {
  policy: ["access-controls", "policy"] as const,
  rules: ["access-controls", "rules"] as const,
  invites: ["access-controls", "invites"] as const,
  capabilities: ["access-controls", "capabilities"] as const,
  entitlements: ["access-controls", "entitlements"] as const,
  usage: ["access-controls", "usage"] as const,
  mine: ["access-controls", "mine"] as const,
};

export function usePlatformPolicy() {
  return useQuery({ queryKey: keys.policy, queryFn: async () => (await api.get("/v1/admin/platform-policy")).data as PlatformPolicy });
}

export function useUpdatePlatformPolicy() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { admissionMode?: PlatformPolicy["effectiveAdmissionMode"]; aiControlsEnabled?: boolean }) =>
      (await api.patch("/v1/admin/platform-policy", payload)).data as PlatformPolicy,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.policy });
      client.invalidateQueries({ queryKey: ["system-config"] });
    },
  });
}

export function useAdmissionRules() {
  return useQuery({ queryKey: keys.rules, queryFn: async () => (await api.get("/v1/admin/admission-rules")).data as AdmissionRule[] });
}

export function useCreateAdmissionRule() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { kind: "email" | "domain"; value: string }) =>
      (await api.post("/v1/admin/admission-rules", payload)).data as AdmissionRule,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.rules }),
  });
}

export function useDeleteAdmissionRule() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.delete(`/v1/admin/admission-rules/${id}`),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.rules }),
  });
}

export function useRegistrationInvites() {
  return useQuery({ queryKey: keys.invites, queryFn: async () => (await api.get("/v1/admin/invites")).data as RegistrationInvite[] });
}

export function useCreateRegistrationInvite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      email: string;
      expiresInDays: number;
      sendEmail?: boolean;
    }) => (await api.post("/v1/admin/invites", payload)).data as InviteSecret,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.invites }),
  });
}

export function useRevokeRegistrationInvite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.post(`/v1/admin/invites/${id}/revoke`)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.invites }),
  });
}

export function useCapabilityCostPolicies() {
  return useQuery({ queryKey: keys.capabilities, queryFn: async () => (await api.get("/v1/admin/capability-cost-policies")).data as CapabilityCostPolicy[] });
}

export function useUpdateCapabilityCostPolicy() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { capabilityDefinitionId: string; classification: "unmetered" | "ai"; costUnits: number }) =>
      (await api.put(`/v1/admin/capability-cost-policies/${payload.capabilityDefinitionId}`, {
        classification: payload.classification,
        costUnits: payload.costUnits,
      })).data as CapabilityCostPolicy,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.capabilities });
      client.invalidateQueries({ queryKey: ["extensions", "capabilities"] });
    },
  });
}

export function useAIEntitlements() {
  return useQuery({ queryKey: keys.entitlements, queryFn: async () => (await api.get("/v1/admin/ai-entitlements")).data as AIEntitlement[] });
}

export function useUpdateAIEntitlement() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { userId: string; state: AIEntitlement["state"]; monthlyLimitUnits: number | null }) =>
      (await api.put(`/v1/admin/users/${payload.userId}/ai-entitlement`, {
        state: payload.state,
        monthlyLimitUnits: payload.monthlyLimitUnits,
      })).data as AIEntitlement,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.entitlements });
      client.invalidateQueries({ queryKey: keys.mine });
    },
  });
}

export function useAIUsage() {
  return useQuery({ queryKey: keys.usage, queryFn: async () => (await api.get("/v1/admin/ai-usage")).data as AIUsage });
}

export function useMyAIEntitlement(enabled = true) {
  return useQuery({
    queryKey: keys.mine,
    queryFn: async () => (await api.get("/v1/ai/entitlement")).data as Omit<AIEntitlement, "userId" | "userName" | "userEmail">,
    enabled,
  });
}

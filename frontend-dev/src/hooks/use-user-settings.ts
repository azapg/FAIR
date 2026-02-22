import {
  useMutation,
  useQueries,
  useQueryClient,
} from "@tanstack/react-query";

import api from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export type UserSettings = Record<string, unknown>;

type UserSettingsResponse = {
  settings: UserSettings;
};

type AuthMeResponse = {
  preferences?: {
    interfaceMode?: "simple" | "expert";
  };
};

export const userSettingsKeys = {
  all: ["user-settings"] as const,
  me: () => [...userSettingsKeys.all, "me"] as const,
  authMe: () => [...userSettingsKeys.all, "auth-me"] as const,
};

const fetchMySettings = async (): Promise<UserSettings> => {
  const res = await api.get<UserSettingsResponse>("/users/me/settings");
  return res.data?.settings ?? {};
};

const fetchAuthMe = async (): Promise<AuthMeResponse> => {
  const res = await api.get<AuthMeResponse>("/auth/me");
  return res.data ?? {};
};

const patchMySettings = async (settings: UserSettings): Promise<UserSettings> => {
  const res = await api.patch<UserSettingsResponse>("/users/me/settings", {
    settings,
  });
  return res.data?.settings ?? {};
};

const getValueAtPath = (source: UserSettings, path: string): unknown => {
  const keys = path
    .split(".")
    .map((key) => key.trim())
    .filter(Boolean);

  if (keys.length === 0) return undefined;

  let cursor: unknown = source;
  for (const key of keys) {
    if (typeof cursor !== "object" || cursor === null || !(key in cursor)) {
      return undefined;
    }
    cursor = (cursor as Record<string, unknown>)[key];
  }
  return cursor;
};

const normalizeFallbackSettings = (
  authMe: AuthMeResponse | undefined,
): UserSettings => ({
  preferences: {
    interfaceMode: authMe?.preferences?.interfaceMode ?? "simple",
  },
});

export function useUserSettings(enabled = true) {
  const { isAuthenticated } = useAuth();
  const isEnabled = enabled && isAuthenticated;

  const [settingsQuery, authMeQuery] = useQueries({
    queries: [
      {
        queryKey: userSettingsKeys.me(),
        queryFn: fetchMySettings,
        enabled: isEnabled,
      },
      {
        queryKey: userSettingsKeys.authMe(),
        queryFn: fetchAuthMe,
        enabled: isEnabled,
      },
    ],
  });

  const fallback = normalizeFallbackSettings(authMeQuery.data);
  const settings = settingsQuery.data ?? fallback;

  return {
    settings,
    settingsQuery,
    authMeQuery,
    isLoading: settingsQuery.isLoading || authMeQuery.isLoading,
    isFetching: settingsQuery.isFetching || authMeQuery.isFetching,
  };
}

export function useUserSetting<T = unknown>(path: string, fallback?: T) {
  const { settings, ...query } = useUserSettings();
  const value = getValueAtPath(settings, path) as T | undefined;

  return {
    ...query,
    value: (value === undefined ? fallback : value) as T,
  };
}

export function useUpdateUserSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: UserSettings) => patchMySettings(settings),
    onSuccess: (settings) => {
      queryClient.setQueryData(userSettingsKeys.me(), settings);
      queryClient.invalidateQueries({ queryKey: userSettingsKeys.authMe() });
    },
  });
}

import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";

import api from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export type UserSettings = Record<string, unknown>;

type UserSettingsResponse = {
  settings: UserSettings;
};

type AuthMeResponse = {
  settings?: UserSettings;
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

const getPathKeys = (path: string): string[] =>
  path
    .split(".")
    .map((key) => key.trim())
    .filter(Boolean);

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const getValueAtPath = (source: UserSettings, path: string): unknown => {
  const keys = getPathKeys(path);
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

/**
 * Immutably sets a value at a specified nested path within a UserSettings object.
 *
 * This function creates a new UserSettings object with the value updated at the given path,
 * without modifying the original source object. It handles nested paths by creating
 * intermediate objects as needed.
 *
 * @param source - The original UserSettings object to update.
 * @param path - A dot-separated string representing the nested path (e.g., "theme.color.primary").
 * @param value - The value to set at the specified path. Can be of any type.
 * @returns A new UserSettings object with the value set at the path.
 *
 * @example
 * const settings = { theme: { color: { primary: 'blue' } } };
 * const updated = setValueAtPath(settings, 'theme.color.secondary', 'green');
 * // updated: { theme: { color: { primary: 'blue', secondary: 'green' } } }
 * // settings remains unchanged
 */
export const setValueAtPath = (
  source: UserSettings,
  path: string,
  value: unknown,
): UserSettings => {
  const keys = getPathKeys(path);
  if (keys.length === 0) return source;

  // shallow copy of the source to ensure immutability
  const result: UserSettings = { ...source };
  let cursor: Record<string, unknown> = result;

  // Traverse the path, creating nested objects as needed (stop before the last key)
  for (let i = 0; i < keys.length - 1; i += 1) {
    const key = keys[i];
    const existing = cursor[key];
    // If existing is an object, shallow copy it; otherwise, create an empty object
    // This ensures we don't mutate the original nested objects
    cursor[key] = isObject(existing) ? { ...existing } : {};
    // Move the cursor down to the newly assigned object
    cursor = cursor[key] as Record<string, unknown>;
  }

  // Set the value at the final key in the path
  cursor[keys[keys.length - 1]] = value;
  return result;
};


const mergeDeep = (
  source: Record<string, unknown>,
  patch: Record<string, unknown>,
): Record<string, unknown> => {
  const result: Record<string, unknown> = { ...source };

  for (const [key, value] of Object.entries(patch)) {
    const existing = result[key];
    if (isObject(existing) && isObject(value)) {
      result[key] = mergeDeep(existing, value);
    } else {
      result[key] = value;
    }
  }

  return result;
};

export const mergeSettings = (
  source: UserSettings,
  patch: UserSettings,
): UserSettings => mergeDeep(source, patch);

const normalizeFallbackSettings = (
  authMe: AuthMeResponse | undefined,
): UserSettings => {
  const baseSettings =
    authMe?.settings && typeof authMe.settings === "object" ? authMe.settings : {};

  return mergeDeep(
    {
      preferences: {
        interfaceMode: "simple",
        simpleView: false,
        devMode: false,
        theme: "system",
        language: "en",
      },
    },
    baseSettings,
  );
};

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

export function useUpdateUserSetting() {
  const { settings } = useUserSettings();
  const updateSettings = useUpdateUserSettings();

  return useMutation({
    mutationFn: async ({ path, value }: { path: string; value: unknown }) =>
      updateSettings.mutateAsync(setValueAtPath(settings, path, value)),
  });
}

export function usePatchUserSettings() {
  const { settings } = useUserSettings();
  const updateSettings = useUpdateUserSettings();

  return useMutation({
    mutationFn: async (patch: UserSettings) =>
      updateSettings.mutateAsync(mergeSettings(settings, patch)),
  });
}

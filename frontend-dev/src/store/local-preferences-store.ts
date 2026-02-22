import { create } from "zustand";
import { persist } from "zustand/middleware";

export type LocalPreferences = Record<string, unknown>;

type LocalPreferencesState = {
  preferences: LocalPreferences;
};

type LocalPreferencesActions = {
  setPreference: (path: string, value: unknown) => void;
  removePreference: (path: string) => void;
  resetPreferences: () => void;
};

const splitPath = (path: string): string[] =>
  path
    .split(".")
    .map((key) => key.trim())
    .filter(Boolean);

export const getPreferenceAtPath = (
  source: LocalPreferences,
  path: string,
): unknown => {
  const keys = splitPath(path);
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

const setPreferenceAtPath = (
  source: LocalPreferences,
  path: string,
  value: unknown,
): LocalPreferences => {
  const keys = splitPath(path);
  if (keys.length === 0) return source;

  const result: LocalPreferences = { ...source };
  let cursor: Record<string, unknown> = result;

  for (let i = 0; i < keys.length - 1; i += 1) {
    const key = keys[i];
    const existing = cursor[key];
    cursor[key] =
      typeof existing === "object" && existing !== null
        ? { ...(existing as Record<string, unknown>) }
        : {};
    cursor = cursor[key] as Record<string, unknown>;
  }

  cursor[keys[keys.length - 1]] = value;
  return result;
};

const removePreferenceAtPath = (
  source: LocalPreferences,
  path: string,
): LocalPreferences => {
  const keys = splitPath(path);
  if (keys.length === 0) return source;

  const result: LocalPreferences = { ...source };
  let cursor: Record<string, unknown> = result;

  for (let i = 0; i < keys.length - 1; i += 1) {
    const key = keys[i];
    const existing = cursor[key];
    if (typeof existing !== "object" || existing === null) {
      return source;
    }
    cursor[key] = { ...(existing as Record<string, unknown>) };
    cursor = cursor[key] as Record<string, unknown>;
  }

  delete cursor[keys[keys.length - 1]];
  return result;
};

export const useLocalPreferencesStore = create<
  LocalPreferencesState & LocalPreferencesActions
>()(
  persist(
    (set) => ({
      preferences: {},
      setPreference: (path, value) =>
        set((state) => ({
          preferences: setPreferenceAtPath(state.preferences, path, value),
        })),
      removePreference: (path) =>
        set((state) => ({
          preferences: removePreferenceAtPath(state.preferences, path),
        })),
      resetPreferences: () => set({ preferences: {} }),
    }),
    {
      name: "fair-local-preferences",
    },
  ),
);

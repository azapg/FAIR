import { useMemo } from "react";

import {
  getPreferenceAtPath,
  useLocalPreferencesStore,
} from "@/store/local-preferences-store";

export function useLocalPreference<T = unknown>(path: string, fallback?: T) {
  const value = useLocalPreferencesStore((state) =>
    getPreferenceAtPath(state.preferences, path),
  ) as T | undefined;
  const setPreference = useLocalPreferencesStore((state) => state.setPreference);
  const removePreference = useLocalPreferencesStore(
    (state) => state.removePreference,
  );

  const resolvedValue = useMemo(
    () => (value === undefined ? fallback : value),
    [fallback, value],
  );

  return {
    value: resolvedValue as T,
    setValue: (nextValue: T) => setPreference(path, nextValue),
    removeValue: () => removePreference(path),
  };
}

export function useLocalPreferences() {
  const preferences = useLocalPreferencesStore((state) => state.preferences);
  const setPreference = useLocalPreferencesStore((state) => state.setPreference);
  const removePreference = useLocalPreferencesStore(
    (state) => state.removePreference,
  );
  const resetPreferences = useLocalPreferencesStore(
    (state) => state.resetPreferences,
  );

  return {
    preferences,
    setPreference,
    removePreference,
    resetPreferences,
  };
}

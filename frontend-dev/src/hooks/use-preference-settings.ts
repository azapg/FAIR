import { useTheme } from "@/components/theme-provider";
import { useTranslation } from "react-i18next";

import { useLocalPreference } from "@/hooks/use-local-preference";
import { useUpdateUserSetting, useUserSetting } from "@/hooks/use-user-settings";
import { useAuth } from "@/contexts/auth-context";

export type ThemeMode = "system" | "light" | "dark";
export type LanguageCode = "en" | "es";

const normalizeLanguage = (lang: string | undefined): LanguageCode =>
  lang?.toLowerCase().startsWith("es") ? "es" : "en";

export function usePreferenceSettings() {
  const { theme, setTheme } = useTheme();
  const { i18n } = useTranslation();
  const { isAuthenticated } = useAuth();
  const updateSetting = useUpdateUserSetting();

  const localTheme = useLocalPreference<ThemeMode | undefined>("ui.theme").value;
  const localLanguage = useLocalPreference<LanguageCode | undefined>("ui.language").value;
  const localSimpleView = useLocalPreference<boolean | undefined>("ui.simpleView").value;

  const setLocalTheme = useLocalPreference<ThemeMode>("ui.theme").setValue;
  const setLocalLanguage = useLocalPreference<LanguageCode>("ui.language").setValue;
  const setLocalSimpleView = useLocalPreference<boolean>("ui.simpleView").setValue;

  const serverTheme = useUserSetting<ThemeMode>("preferences.theme", "system").value;
  const serverLanguage = useUserSetting<LanguageCode>("preferences.language", "en").value;
  const serverSimpleView = useUserSetting<boolean>("preferences.simpleView", false).value;

  const effectiveTheme = localTheme ?? serverTheme ?? (theme as ThemeMode);
  const effectiveLanguage = localLanguage ?? serverLanguage ?? normalizeLanguage(i18n.language);
  const effectiveSimpleView = localSimpleView ?? serverSimpleView ?? false;

  const setThemePreference = (nextTheme: ThemeMode) => {
    setTheme(nextTheme);
    setLocalTheme(nextTheme);
    if (isAuthenticated) {
      updateSetting.mutate({ path: "preferences.theme", value: nextTheme });
    }
  };

  const setLanguagePreference = (nextLanguage: LanguageCode) => {
    i18n.changeLanguage(nextLanguage);
    setLocalLanguage(nextLanguage);
    if (isAuthenticated) {
      updateSetting.mutate({ path: "preferences.language", value: nextLanguage });
    }
  };

  const setSimpleViewPreference = (enabled: boolean) => {
    setLocalSimpleView(enabled);
    if (isAuthenticated) {
      updateSetting.mutate({ path: "preferences.simpleView", value: enabled });
    }
  };

  return {
    effectiveTheme,
    effectiveLanguage,
    effectiveSimpleView,
    setThemePreference,
    setLanguagePreference,
    setSimpleViewPreference,
    isSaving: updateSetting.isPending,
  };
}

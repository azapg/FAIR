import {QueryClientProvider} from "@tanstack/react-query";
import {queryClient} from "@/lib/query-client";
import {AuthProvider} from "@/contexts/auth-context";
import {ThemeProvider} from "@/components/theme-provider"
import {ReactNode, useEffect} from "react";
import {SessionSocketProvider} from "@/contexts/session-socket-context";
import {useVersionCheck} from "@/hooks/use-version";
import { useTheme } from "@/components/theme-provider";
import { useTranslation } from "react-i18next";
import { useLocalPreference } from "@/hooks/use-local-preference";
import { useUserSetting } from "@/hooks/use-user-settings";
import type { LanguageCode, ThemeMode } from "@/hooks/use-preference-settings";


function VersionChecker() {
  useVersionCheck();
  return null;
}

function SettingsRuntime() {
  const { theme, setTheme } = useTheme();
  const { i18n } = useTranslation();

  const { value: localTheme, setValue: setLocalTheme } =
    useLocalPreference<ThemeMode | undefined>("ui.theme");
  const { value: localLanguage, setValue: setLocalLanguage } =
    useLocalPreference<LanguageCode | undefined>("ui.language");
  const { value: localSimpleView, setValue: setLocalSimpleView } =
    useLocalPreference<boolean | undefined>("ui.simpleView");
  const { value: localDevMode, setValue: setLocalDevMode } =
    useLocalPreference<boolean | undefined>("ui.devMode");

  const themeServer = useUserSetting<ThemeMode>("preferences.theme", "system").value;
  const languageServer = useUserSetting<LanguageCode>("preferences.language", "en").value;
  const simpleViewServer = useUserSetting<boolean>("preferences.simpleView", false).value;
  const devModeServer = useUserSetting<boolean>("preferences.devMode", false).value;

  const resolvedTheme = localTheme ?? themeServer;
  const resolvedLanguage = localLanguage ?? languageServer;
  const resolvedSimpleView = localSimpleView ?? simpleViewServer;
  const resolvedDevMode = localDevMode ?? devModeServer;

  useEffect(() => {
    if (localTheme === undefined) {
      setLocalTheme(themeServer);
    }
  }, [localTheme, setLocalTheme, themeServer]);

  useEffect(() => {
    if (localLanguage === undefined) {
      setLocalLanguage(languageServer);
    }
  }, [languageServer, localLanguage, setLocalLanguage]);

  useEffect(() => {
    if (localSimpleView === undefined) {
      setLocalSimpleView(simpleViewServer);
    }
  }, [localSimpleView, setLocalSimpleView, simpleViewServer]);

  useEffect(() => {
    if (localDevMode === undefined) {
      setLocalDevMode(devModeServer);
    }
  }, [devModeServer, localDevMode, setLocalDevMode]);

  useEffect(() => {
    if (theme !== resolvedTheme) {
      setTheme(resolvedTheme);
    }
  }, [resolvedTheme, setTheme, theme]);

  useEffect(() => {
    if (!i18n.language.toLowerCase().startsWith(resolvedLanguage)) {
      i18n.changeLanguage(resolvedLanguage);
    }
  }, [i18n, resolvedLanguage]);

  useEffect(() => {
    document.documentElement.classList.toggle("simple-view", Boolean(resolvedSimpleView));
  }, [resolvedSimpleView]);

  useEffect(() => {
    document.documentElement.classList.toggle("dev-mode", Boolean(resolvedDevMode));
  }, [resolvedDevMode]);

  return null;
}

export function Providers({children}: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionSocketProvider>
        <ThemeProvider defaultTheme={"system"}>
          <AuthProvider>
            <VersionChecker />
            <SettingsRuntime />
            {children}
          </AuthProvider>
        </ThemeProvider>
      </SessionSocketProvider>
    </QueryClientProvider>
  );
}

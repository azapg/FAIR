import { useTranslation } from "react-i18next";

import { useTheme } from "@/components/theme-provider";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";

export function PreferencesSection() {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useTheme();

  return (
    <SettingsSectionCard
      title={t("settings.sections.preferences.title")}
      description={t("settings.sections.preferences.description")}
    >
      <div className="space-y-2">
        <Label htmlFor="settings-theme">{t("settings.fields.theme")}</Label>
        <Select
          value={theme}
          onValueChange={(value) => setTheme(value as "light" | "dark" | "system")}
        >
          <SelectTrigger id="settings-theme" className="w-full">
            <SelectValue placeholder={t("settings.fields.theme")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="light">{t("theme.light")}</SelectItem>
            <SelectItem value="dark">{t("theme.dark")}</SelectItem>
            <SelectItem value="system">{t("theme.system")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="settings-language">{t("settings.fields.language")}</Label>
        <Select
          value={i18n.language.toLowerCase().startsWith("es") ? "es" : "en"}
          onValueChange={(value) => i18n.changeLanguage(value)}
        >
          <SelectTrigger id="settings-language" className="w-full">
            <SelectValue placeholder={t("settings.fields.language")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="en">{t("settings.languages.en")}</SelectItem>
            <SelectItem value="es">{t("settings.languages.es")}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </SettingsSectionCard>
  );
}

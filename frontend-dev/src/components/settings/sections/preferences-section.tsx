import { useTranslation } from "react-i18next";

import { usePreferenceSettings } from "@/hooks/use-preference-settings";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";

export function PreferencesSection() {
  const { t } = useTranslation();
  const {
    effectiveTheme,
    effectiveLanguage,
    effectiveSimpleView,
    setThemePreference,
    setLanguagePreference,
    setSimpleViewPreference,
    isSaving,
  } = usePreferenceSettings();

  return (
    <SettingsSectionCard
      title={t("settings.sections.preferences.title")}
      description={t("settings.sections.preferences.description")}
    >
      <div className="space-y-2">
        <Label htmlFor="settings-theme">{t("settings.fields.theme")}</Label>
        <Select
          value={effectiveTheme}
          onValueChange={(value) => setThemePreference(value as "light" | "dark" | "system")}
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
          value={effectiveLanguage}
          onValueChange={(value) => setLanguagePreference(value as "en" | "es")}
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

      <div className="flex items-start justify-between gap-3 py-1">
        <div className="space-y-1">
          <Label htmlFor="settings-simple-view">{t("settings.fields.simpleView")}</Label>
          <p className="text-xs text-muted-foreground">
            {t("settings.fields.simpleViewDescription")}
          </p>
        </div>
        <Switch
          id="settings-simple-view"
          checked={effectiveSimpleView}
          onCheckedChange={(checked) => setSimpleViewPreference(Boolean(checked))}
          disabled={isSaving}
        />
      </div>
    </SettingsSectionCard>
  );
}

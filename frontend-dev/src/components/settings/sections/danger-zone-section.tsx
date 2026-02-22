import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";

export function DangerZoneSection() {
  const { t } = useTranslation();

  return (
    <SettingsSectionCard
      title={t("settings.sections.dangerZone.title")}
      description={t("settings.sections.dangerZone.description")}
    >
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
        <p className="text-sm text-muted-foreground">
          {t("settings.sections.dangerZone.warning")}
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="destructive">{t("settings.sections.dangerZone.deleteAccount")}</Button>
          <Button variant="outline">{t("settings.sections.dangerZone.exportData")}</Button>
        </div>
      </div>
    </SettingsSectionCard>
  );
}

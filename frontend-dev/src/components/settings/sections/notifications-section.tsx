import { useTranslation } from "react-i18next";

import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";
import { IfSetting } from "@/components/if-setting";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  getValueAtPath,
  useUpdateUserSetting,
  useUserSettings,
} from "@/hooks/use-user-settings";

const NOTIFICATION_GROUPS = [
  {
    titleKey: "settings.notifications.groups.gradingAi",
    items: [
      { key: "batchCompletion", labelKey: "settings.notifications.batchCompletion" },
      { key: "lowConfidenceFlags", labelKey: "settings.notifications.lowConfidenceFlags" },
      { key: "plagiarismDetection", labelKey: "settings.notifications.plagiarismDetection" },
      { key: "tokenQuotaLimits", labelKey: "settings.notifications.tokenQuotaLimits" },
    ],
  },
  {
    titleKey: "settings.notifications.groups.studentActivity",
    items: [
      { key: "newSubmissions", labelKey: "settings.notifications.newSubmissions" },
      { key: "lateSubmissions", labelKey: "settings.notifications.lateSubmissions" },
      { key: "feedbackRead", labelKey: "settings.notifications.feedbackRead" },
      { key: "regradeRequests", labelKey: "settings.notifications.regradeRequests" },
    ],
  },
  {
    titleKey: "settings.notifications.groups.collaboration",
    items: [
      { key: "rubricChanges", labelKey: "settings.notifications.rubricChanges" },
      { key: "gradeOverrides", labelKey: "settings.notifications.gradeOverrides" },
      { key: "newCourseInvites", labelKey: "settings.notifications.newCourseInvites" },
    ],
  },
  {
    titleKey: "settings.notifications.groups.systemDelivery",
    items: [
      { key: "dailyDigest", labelKey: "settings.notifications.dailyDigest" },
      { key: "browserNotifications", labelKey: "settings.notifications.browserNotifications" },
      { key: "platformUpdates", labelKey: "settings.notifications.platformUpdates" },
    ],
  },
] as const;

export function NotificationsSection() {
  const { t } = useTranslation();
  const updateSetting = useUpdateUserSetting();
  const { settings } = useUserSettings();

  return (
    <SettingsSectionCard
      title={t("settings.sections.notifications.title")}
      description={t("settings.sections.notifications.description")}
    >
      {NOTIFICATION_GROUPS.map((group) => (
        <div key={group.titleKey} className="space-y-2">
          <h4 className="text-sm font-semibold text-foreground">{t(group.titleKey)}</h4>
          <div className="space-y-1">
            {group.items.map((item) => {
              const path = `notifications.${item.key}`;
              const enabled = Boolean(getValueAtPath(settings, path) ?? false);
              const row = (
                <div key={item.key} className="flex items-center justify-between py-1">
                  <Label htmlFor={`settings-${item.key}`}>{t(item.labelKey)}</Label>
                  <Switch
                    id={`settings-${item.key}`}
                    checked={enabled}
                    onCheckedChange={(checked) =>
                      updateSetting.mutate({
                        path,
                        value: Boolean(checked),
                      })
                    }
                  />
                </div>
              );

              if (item.key === "dailyDigest") {
                return (
                  <IfSetting
                    key={item.key}
                    setting="features.emailEnabled"
                    scope="local"
                  >
                    {row}
                  </IfSetting>
                );
              }

              return row;
            })}
          </div>
        </div>
      ))}
    </SettingsSectionCard>
  );
}

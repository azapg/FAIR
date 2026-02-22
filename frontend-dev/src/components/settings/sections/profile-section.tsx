import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/auth-context";
import UserAvatar from "@/components/user-avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";

export function ProfileSection() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const userName = user?.name ?? t("header.profile");
  const userEmail = user?.email ?? "";

  return (
    <SettingsSectionCard
      title={t("settings.sections.profile.title")}
      description={t("settings.sections.profile.description")}
    >
      <div className="flex items-center gap-4 rounded-lg border p-4">
        <UserAvatar avatarSrc={null} username={userName} className="h-16 w-16 rounded-xl" />
        <div className="space-y-2">
          <p className="text-sm font-medium">{userName}</p>
          <Button variant="outline" size="sm">
            {t("settings.sections.profile.avatarAction")}
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="settings-profile-email">{t("settings.fields.email")}</Label>
        <Input id="settings-profile-email" value={userEmail} readOnly />
      </div>

      <div className="space-y-2">
        <Label htmlFor="settings-profile-password">{t("settings.fields.password")}</Label>
        <Button id="settings-profile-password" variant="outline">
          {t("settings.sections.profile.changePassword")}
        </Button>
      </div>
    </SettingsSectionCard>
  );
}

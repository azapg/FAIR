import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/auth-context";
import UserAvatar from "@/components/user-avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";
import { useState } from "react";

export function ProfileSection() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [random, setRandom] = useState<number | null>(null);
  const userName = user?.name ?? t("header.profile");
  const userEmail = user?.email ?? "";

  const regenerateAvatar = () => {
    setRandom((prev) => (prev === null ? 1 : prev + 1)  );
  }


  return (
    <SettingsSectionCard
      title={t("settings.sections.profile.title")}
      description={t("settings.sections.profile.description")}
    >
      <div className="flex flex-col justify-center rounded-lg gap-2">
        <div className="flex gap-4">
          <UserAvatar size="xl" avatarSrc={null} username={userName + (random ? ` (${random})` : "")} />
          <div className="space-y-2">
            {t("settings.sections.profile.yourName")}
            <Input value={userName} disabled />
          </div>
        </div>
        <div>
          <Button variant="link" className="p-0 h-auto text-blue-500">{t("settings.sections.profile.addProfilePictureAction")}</Button> {t("common.or")} <Button variant="link" className="p-0 h-auto text-blue-500" onClick={regenerateAvatar}>{t("settings.sections.profile.generateProfilePictureAction")}</Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <Label htmlFor="settings-profile-email">{t("settings.fields.email")}</Label>
          <span className="text-sm text-muted-foreground">{userEmail}</span>
        </div>
        <Button id="settings-profile-password" variant="outline">
          {t("settings.sections.profile.changeEmail")}
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="settings-profile-password">{t("settings.fields.password")}</Label>
        <Button id="settings-profile-password" variant="outline">
          {t("settings.sections.profile.changePassword")}
        </Button>
      </div>
    </SettingsSectionCard>
  );
}

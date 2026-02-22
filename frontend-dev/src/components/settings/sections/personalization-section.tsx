import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useUpdateUserSetting, useUserSetting } from "@/hooks/use-user-settings";

type Personality = "default" | "professional" | "friendly";

export function PersonalizationSection() {
  const { t } = useTranslation();
  const updateSetting = useUpdateUserSetting();

  const personality = useUserSetting<Personality>(
    "ai.personalization.chatPersonality",
    "default",
  ).value;
  const aboutYouValue = useUserSetting<string>("ai.personalization.aboutYou", "").value;
  const persistentMemory = useUserSetting<boolean>(
    "ai.personalization.persistentMemory",
    false,
  ).value;

  const [aboutYouDraft, setAboutYouDraft] = useState(aboutYouValue);

  useEffect(() => {
    setAboutYouDraft(aboutYouValue);
  }, [aboutYouValue]);

  return (
    <SettingsSectionCard
      title={t("settings.sections.personalization.title")}
      description={t("settings.sections.personalization.description")}
    >
      <div className="space-y-2">
        <Label htmlFor="settings-chat-personality">{t("settings.ai.chatPersonality")}</Label>
        <Select
          value={personality}
          onValueChange={(value) =>
            updateSetting.mutate({
              path: "ai.personalization.chatPersonality",
              value,
            })
          }
        >
          <SelectTrigger id="settings-chat-personality" className="w-full">
            <SelectValue placeholder={t("settings.ai.chatPersonality")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="default">{t("settings.ai.chatPersonalityOptions.default")}</SelectItem>
            <SelectItem value="professional">
              {t("settings.ai.chatPersonalityOptions.professional")}
            </SelectItem>
            <SelectItem value="friendly">{t("settings.ai.chatPersonalityOptions.friendly")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="settings-about-you">{t("settings.ai.aboutYou")}</Label>
        <Textarea
          id="settings-about-you"
          value={aboutYouDraft}
          onChange={(event) => setAboutYouDraft(event.target.value)}
          onBlur={() =>
            updateSetting.mutate({
              path: "ai.personalization.aboutYou",
              value: aboutYouDraft.trim(),
            })
          }
          placeholder={t("settings.ai.aboutYouPlaceholder")}
          className="min-h-28"
        />
      </div>

      <div className="flex items-start justify-between gap-3 py-1">
        <div className="space-y-1">
          <Label htmlFor="settings-persistent-memory">{t("settings.ai.persistentMemory")}</Label>
          <p className="text-xs text-muted-foreground">
            {t("settings.ai.persistentMemoryDescription")}
          </p>
        </div>
        <Switch
          id="settings-persistent-memory"
          checked={persistentMemory}
          onCheckedChange={(checked) =>
            updateSetting.mutate({
              path: "ai.personalization.persistentMemory",
              value: Boolean(checked),
            })
          }
        />
      </div>
    </SettingsSectionCard>
  );
}

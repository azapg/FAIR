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
import { useUpdateUserSetting, useUserSetting } from "@/hooks/use-user-settings";

const MODEL_OPTIONS = ["gpt-5", "gpt-5-mini", "gpt-4.1"] as const;

type ModelOption = (typeof MODEL_OPTIONS)[number];

export function AiModelsSection() {
  const { t } = useTranslation();
  const updateSetting = useUpdateUserSetting();

  const webSearch = useUserSetting<boolean>("ai.models.webSearch", true).value;
  const defaultModel = useUserSetting<ModelOption>("ai.models.defaultModel", "gpt-5-mini").value;

  return (
    <SettingsSectionCard
      title={t("settings.sections.aiModels.title")}
      description={t("settings.sections.aiModels.description")}
    >
      <div className="flex items-start justify-between gap-3 py-1">
        <div className="space-y-1">
          <Label htmlFor="settings-web-search">{t("settings.ai.webSearch")}</Label>
          <p className="text-xs text-muted-foreground">{t("settings.ai.webSearchDescription")}</p>
        </div>
        <Switch
          id="settings-web-search"
          checked={webSearch}
          onCheckedChange={(checked) =>
            updateSetting.mutate({
              path: "ai.models.webSearch",
              value: Boolean(checked),
            })
          }
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="settings-default-model">{t("settings.ai.defaultModel")}</Label>
        <Select
          value={defaultModel}
          onValueChange={(value) =>
            updateSetting.mutate({
              path: "ai.models.defaultModel",
              value,
            })
          }
        >
          <SelectTrigger id="settings-default-model" className="w-full">
            <SelectValue placeholder={t("settings.ai.defaultModel")} />
          </SelectTrigger>
          <SelectContent>
            {MODEL_OPTIONS.map((model) => (
              <SelectItem key={model} value={model}>
                {model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </SettingsSectionCard>
  );
}

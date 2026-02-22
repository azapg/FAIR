import type { ComponentType } from "react";

import { AccountSection } from "@/components/settings/sections/account-section";
import { AiModelsSection } from "@/components/settings/sections/ai-models-section";
import { EmptySectionFromKeys } from "@/components/settings/sections/empty-section";
import { NotificationsSection } from "@/components/settings/sections/notifications-section";
import { PersonalizationSection } from "@/components/settings/sections/personalization-section";
import { PreferencesSection } from "@/components/settings/sections/preferences-section";

export type SettingsCategoryId = "you" | "ai" | "research" | "admin";

export type SettingsSectionId =
  | "account"
  | "preferences"
  | "notifications"
  | "personalization"
  | "ai-models"
  | "api-keys"
  | "admin-people"
  | "admin-models";

export type SettingsSectionDefinition = {
  id: SettingsSectionId;
  category: SettingsCategoryId;
  groupKey?: string;
  titleKey: string;
  descriptionKey: string;
  render: ComponentType;
};

export const SETTINGS_CATEGORY_ORDER: SettingsCategoryId[] = ["you", "ai", "research", "admin"];

export const SETTINGS_SECTIONS: SettingsSectionDefinition[] = [
  {
    id: "account",
    category: "you",
    titleKey: "settings.sections.account.title",
    descriptionKey: "settings.sections.account.description",
    render: AccountSection,
  },
  {
    id: "preferences",
    category: "you",
    titleKey: "settings.sections.preferences.title",
    descriptionKey: "settings.sections.preferences.description",
    render: PreferencesSection,
  },
  {
    id: "notifications",
    category: "you",
    titleKey: "settings.sections.notifications.title",
    descriptionKey: "settings.sections.notifications.description",
    render: NotificationsSection,
  },
  {
    id: "personalization",
    category: "ai",
    titleKey: "settings.sections.personalization.title",
    descriptionKey: "settings.sections.personalization.description",
    render: PersonalizationSection,
  },
  {
    id: "ai-models",
    category: "ai",
    titleKey: "settings.sections.aiModels.title",
    descriptionKey: "settings.sections.aiModels.description",
    render: AiModelsSection,
  },
  {
    id: "api-keys",
    category: "research",
    titleKey: "settings.sections.apiKeys.title",
    descriptionKey: "settings.sections.apiKeys.description",
    render: () => (
      <EmptySectionFromKeys
        titleKey="settings.sections.apiKeys.title"
        descriptionKey="settings.sections.apiKeys.description"
      />
    ),
  },
  {
    id: "admin-people",
    category: "admin",
    titleKey: "settings.sections.adminPeople.title",
    descriptionKey: "settings.sections.adminPeople.description",
    render: () => (
      <EmptySectionFromKeys
        titleKey="settings.sections.adminPeople.title"
        descriptionKey="settings.sections.adminPeople.description"
      />
    ),
  },
  {
    id: "admin-models",
    category: "admin",
    titleKey: "settings.sections.adminModels.title",
    descriptionKey: "settings.sections.adminModels.description",
    render: () => (
      <EmptySectionFromKeys
        titleKey="settings.sections.adminModels.title"
        descriptionKey="settings.sections.adminModels.description"
      />
    ),
  },
];

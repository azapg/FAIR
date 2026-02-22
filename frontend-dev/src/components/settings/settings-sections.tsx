import type { ComponentType } from "react";

import { DangerZoneSection } from "@/components/settings/sections/danger-zone-section";
import { EmptySectionFromKeys } from "@/components/settings/sections/empty-section";
import { PreferencesSection } from "@/components/settings/sections/preferences-section";
import { ProfileSection } from "@/components/settings/sections/profile-section";

export type SettingsCategoryId = "you" | "ai" | "research" | "admin";

export type SettingsSectionId =
  | "profile"
  | "danger-zone"
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
    id: "profile",
    category: "you",
    groupKey: "settings.groups.account",
    titleKey: "settings.sections.profile.title",
    descriptionKey: "settings.sections.profile.description",
    render: ProfileSection,
  },
  {
    id: "danger-zone",
    category: "you",
    groupKey: "settings.groups.account",
    titleKey: "settings.sections.dangerZone.title",
    descriptionKey: "settings.sections.dangerZone.description",
    render: DangerZoneSection,
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
    render: () => (
      <EmptySectionFromKeys
        titleKey="settings.sections.notifications.title"
        descriptionKey="settings.sections.notifications.description"
      />
    ),
  },
  {
    id: "personalization",
    category: "ai",
    titleKey: "settings.sections.personalization.title",
    descriptionKey: "settings.sections.personalization.description",
    render: () => (
      <EmptySectionFromKeys
        titleKey="settings.sections.personalization.title"
        descriptionKey="settings.sections.personalization.description"
      />
    ),
  },
  {
    id: "ai-models",
    category: "ai",
    titleKey: "settings.sections.aiModels.title",
    descriptionKey: "settings.sections.aiModels.description",
    render: () => (
      <EmptySectionFromKeys
        titleKey="settings.sections.aiModels.title"
        descriptionKey="settings.sections.aiModels.description"
      />
    ),
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

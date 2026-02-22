import type { ComponentType, ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/components/theme-provider";
import UserAvatar from "@/components/user-avatar";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

type SettingsSectionCardProps = {
  title: string;
  description: string;
  children: ReactNode;
};

function SettingsSectionCard({
  title,
  description,
  children,
}: SettingsSectionCardProps) {
  return (
    <section className="rounded-lg bg-card p-5">
      <header className="mb-4 space-y-1">
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </header>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function InDevelopmentState() {
  const { t } = useTranslation();

  return (
    <Empty className="min-h-[220px] border bg-muted/10">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Sparkles className="size-5" />
        </EmptyMedia>
        <EmptyTitle>{t("settings.empty.title")}</EmptyTitle>
        <EmptyDescription>{t("settings.empty.description")}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}

function ProfileSection() {
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

function DangerZoneSection() {
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

function PreferencesSection() {
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

function EmptySection({ title, description }: { title: string; description: string }) {
  return (
    <SettingsSectionCard title={title} description={description}>
      <InDevelopmentState />
    </SettingsSectionCard>
  );
}

function EmptySectionFromKeys({
  titleKey,
  descriptionKey,
}: {
  titleKey: string;
  descriptionKey: string;
}) {
  const { t } = useTranslation();
  return <EmptySection title={t(titleKey)} description={t(descriptionKey)} />;
}

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

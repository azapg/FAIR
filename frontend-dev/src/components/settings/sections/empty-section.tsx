import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { SettingsSectionCard } from "@/components/settings/sections/settings-section-card";

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

function EmptySection({ title, description }: { title: string; description: string }) {
  return (
    <SettingsSectionCard title={title} description={description}>
      <InDevelopmentState />
    </SettingsSectionCard>
  );
}

export function EmptySectionFromKeys({
  titleKey,
  descriptionKey,
}: {
  titleKey: string;
  descriptionKey: string;
}) {
  const { t } = useTranslation();
  return <EmptySection title={t(titleKey)} description={t(descriptionKey)} />;
}

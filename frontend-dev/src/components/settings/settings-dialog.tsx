import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Can } from "@/components/can";
import {
  SETTINGS_CATEGORY_ORDER,
  SETTINGS_SECTIONS,
  type SettingsCategoryId,
  type SettingsSectionDefinition,
  type SettingsSectionId,
} from "@/components/settings/settings-sections";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

const ADMIN_PERMISSION = "admin";
const DEFAULT_SECTION: SettingsSectionId = "account";

type SettingsDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isMobile: boolean;
};

function sectionIsAdmin(section: SettingsSectionDefinition) {
  return section.category === "admin";
}

function CategoryNavigation({
  category,
  selectedSectionId,
  onSelectSection,
}: {
  category: SettingsCategoryId;
  selectedSectionId: SettingsSectionId;
  onSelectSection: (sectionId: SettingsSectionId) => void;
}) {
  const { t } = useTranslation();
  const sections = SETTINGS_SECTIONS.filter((section) => section.category === category);

  if (sections.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1.5">
      <p className="px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t(`settings.categories.${category}`)}
      </p>
      <div className="space-y-1">
        {sections.map((section) => {
          return (
            <div key={section.id}>
              <button
                type="button"
                className={cn(
                  "w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                  selectedSectionId === section.id && "bg-muted font-medium",
                )}
                onClick={() => onSelectSection(section.id)}
              >
                {t(section.titleKey)}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DesktopSettingsContent() {
  const [selectedSectionId, setSelectedSectionId] = useState<SettingsSectionId>(DEFAULT_SECTION);

  const selectedSection = useMemo(
    () => SETTINGS_SECTIONS.find((section) => section.id === selectedSectionId),
    [selectedSectionId],
  );
  const SelectedSectionComponent = selectedSection?.render;

  return (
    <div className="flex min-h-0 flex-1">
      <aside className="w-72 border-r">
        <ScrollArea className="h-full px-3 py-4">
          <div className="space-y-4">
            {SETTINGS_CATEGORY_ORDER.map((category) =>
              category === "admin" ? (
                <Can I={ADMIN_PERMISSION} key={category}>
                  <CategoryNavigation
                    category={category}
                    selectedSectionId={selectedSectionId}
                    onSelectSection={setSelectedSectionId}
                  />
                </Can>
              ) : (
                <CategoryNavigation
                  key={category}
                  category={category}
                  selectedSectionId={selectedSectionId}
                  onSelectSection={setSelectedSectionId}
                />
              ),
            )}
          </div>
        </ScrollArea>
      </aside>
      <ScrollArea className="h-full flex-1">
        <div className="space-y-4 p-6">
          {selectedSection && sectionIsAdmin(selectedSection) ? (
            <Can I={ADMIN_PERMISSION}>{SelectedSectionComponent ? <SelectedSectionComponent /> : null}</Can>
          ) : SelectedSectionComponent ? (
            <SelectedSectionComponent />
          ) : null}
        </div>
      </ScrollArea>
    </div>
  );
}

function MobileSettingsContent() {
  const { t } = useTranslation();

  return (
    <>
      <DrawerHeader className="border-b text-left">
        <DrawerTitle>{t("settings.title")}</DrawerTitle>
        <DrawerDescription>{t("settings.description")}</DrawerDescription>
      </DrawerHeader>
      <ScrollArea className="h-full">
        <div className="space-y-6 px-4 py-4 pb-8">
          {SETTINGS_CATEGORY_ORDER.map((category) => {
            const sections = SETTINGS_SECTIONS.filter((section) => section.category === category);
            if (sections.length === 0) {
              return null;
            }

            const sectionBlock = (
              <section key={category} className="space-y-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  {t(`settings.categories.${category}`)}
                </h2>
                <div className="space-y-3">
                  {sections.map((section) => {
                    const SectionComponent = section.render;
                    return <SectionComponent key={section.id} />;
                  })}
                </div>
              </section>
            );

            if (category === "admin") {
              return (
                <Can I={ADMIN_PERMISSION} key={category}>
                  {sectionBlock}
                </Can>
              );
            }

            return sectionBlock;
          })}
        </div>
      </ScrollArea>
    </>
  );
}

export function SettingsDialog({ open, onOpenChange, isMobile }: SettingsDialogProps) {
  if (isMobile) {
    return (
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent className="h-[95vh]">
          <MobileSettingsContent />
        </DrawerContent>
      </Drawer>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!flex h-[90vh] !w-[calc(100vw-2rem)] !max-w-[calc(100vw-2rem)] !flex-col gap-0 overflow-hidden p-0 sm:!w-[1200px] sm:!max-w-[1200px]">
        <DesktopSettingsContent />
      </DialogContent>
    </Dialog>
  );
}

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";

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
  DialogClose,
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
      <p className="px-2 text-[13px] leading-4 font-medium uppercase tracking-wide text-muted-foreground">
        {t(`settings.categories.${category}`)}
      </p>
      <div className="space-y-1">
        {sections.map((section) => {
          return (
            <div key={section.id}>
              <button
                type="button"
                aria-current={selectedSectionId === section.id ? "page" : undefined}
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
  const { t } = useTranslation();
  const [selectedSectionId, setSelectedSectionId] = useState<SettingsSectionId>(DEFAULT_SECTION);

  const selectedSection = useMemo(
    () => SETTINGS_SECTIONS.find((section) => section.id === selectedSectionId),
    [selectedSectionId],
  );
  const SelectedSectionComponent = selectedSection?.render;

  return (
    <div className="grid h-full min-h-0 w-full grid-cols-[minmax(14rem,1fr)_minmax(0,46rem)_minmax(5.5rem,1fr)]">
      <aside className="min-w-0 bg-muted/30">
        <ScrollArea className="h-full">
          <div className="ml-auto w-full max-w-60 px-3 py-16">
            <h2 className="mb-5 px-2 text-base leading-5 font-medium">{t("settings.title")}</h2>
            <nav aria-label={t("settings.navigationLabel")} className="space-y-4">
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
            </nav>
          </div>
        </ScrollArea>
      </aside>
      <main className="min-w-0 bg-background">
        <ScrollArea className="h-full">
          <div className="min-h-full space-y-4 px-6 py-16 lg:px-10">
            {selectedSection && sectionIsAdmin(selectedSection) ? (
              <Can I={ADMIN_PERMISSION}>
                {SelectedSectionComponent ? <SelectedSectionComponent /> : null}
              </Can>
            ) : SelectedSectionComponent ? (
              <SelectedSectionComponent />
            ) : null}
          </div>
        </ScrollArea>
      </main>
      <div className="bg-background px-6 py-16">
        <DialogClose
          className="group flex flex-col items-center gap-1.5 text-muted-foreground outline-none"
          aria-label={t("settings.close")}
        >
          <span className="flex size-9 items-center justify-center rounded-full border-2 border-current transition-colors group-hover:text-foreground group-focus-visible:ring-2 group-focus-visible:ring-ring group-focus-visible:ring-offset-2 group-focus-visible:ring-offset-background">
            <X className="size-5" aria-hidden="true" />
          </span>
          <span className="text-[10px] font-medium uppercase tracking-wide" aria-hidden="true">
            Esc
          </span>
        </DialogClose>
      </div>
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
                <h2 className="text-[13px] leading-4 font-medium uppercase tracking-wide text-muted-foreground">
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
  const { t } = useTranslation();

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
      <DialogContent
        showCloseButton={false}
        className="!inset-0 !top-0 !left-0 !block !h-dvh !w-screen !max-w-none !translate-x-0 !translate-y-0 overflow-hidden !rounded-none !border-0 !p-0 !shadow-none data-[state=closed]:!zoom-out-100 data-[state=open]:!zoom-in-100"
      >
        <DialogHeader className="sr-only">
          <DialogTitle>{t("settings.title")}</DialogTitle>
          <DialogDescription>{t("settings.description")}</DialogDescription>
        </DialogHeader>
        <DesktopSettingsContent />
      </DialogContent>
    </Dialog>
  );
}

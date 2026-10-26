import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BookOpen, Search, Settings as SettingsIcon, X } from "lucide-react";

import { useIsMobile } from "@/hooks/use-mobile";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";

type AppSearchProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenSettings: () => void;
};

function SearchSuggestions({
  onCourses,
  onSettings,
}: {
  onCourses: () => void;
  onSettings: () => void;
}) {
  const { t } = useTranslation();

  return (
    <CommandGroup heading="Suggestions">
      <CommandItem onSelect={onCourses}>
        <BookOpen />
        <span>Go to courses</span>
      </CommandItem>
      <CommandItem onSelect={onSettings}>
        <SettingsIcon />
        <span>Open settings</span>
      </CommandItem>
    </CommandGroup>
  );
}

function MobileSearchBody({
  onOpenChange,
  onOpenSettings,
}: Omit<AppSearchProps, "open">) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const close = () => onOpenChange(false);

  const goCourses = () => {
    close();
    navigate("/courses");
  };

  const goSettings = () => {
    close();
    onOpenSettings();
  };

  return (
    <Command className="flex h-full flex-col">
      <CommandList className="flex-1 overflow-y-auto">
        <CommandEmpty>{t("common.noResults")}</CommandEmpty>
        <SearchSuggestions onCourses={goCourses} onSettings={goSettings} />
      </CommandList>
      <div className="flex items-center gap-2 border-t bg-background p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <CommandInput
          value={query}
          onValueChange={setQuery}
          placeholder={t("nav.search")}
          className="h-11 rounded-full border bg-muted px-3"
          autoFocus
        />
        <Button
          size="icon"
          variant="ghost"
          onClick={close}
          aria-label={t("common.close", { defaultValue: "Close" })}
        >
          <X className="size-5" />
        </Button>
      </div>
    </Command>
  );
}

export function AppSearch({ open, onOpenChange, onOpenSettings }: AppSearchProps) {
  const isMobile = useIsMobile();
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (isMobile) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent
          showCloseButton={false}
          className="!inset-0 !top-0 !left-0 !flex !h-dvh !w-screen !max-w-none !translate-x-0 !translate-y-0 !flex-col !gap-0 !overflow-hidden !rounded-none !border-0 !p-0 !shadow-none"
        >
          <DialogHeader className="sr-only">
            <DialogTitle>{t("nav.search")}</DialogTitle>
            <DialogDescription>
              {t("common.searchDescription", {
                defaultValue: "Search navigation and available commands.",
              })}
            </DialogDescription>
          </DialogHeader>
          <MobileSearchBody onOpenChange={onOpenChange} onOpenSettings={onOpenSettings} />
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <CommandDialog
      title={t("nav.search")}
      description={t("common.searchDescription", {
        defaultValue: "Search navigation and available commands.",
      })}
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
      }}
    >
      <Command>
        <CommandInput placeholder={t("nav.search")} />
        <CommandList>
          <CommandEmpty>{t("common.noResults")}</CommandEmpty>
          <SearchSuggestions
            onCourses={() => {
              onOpenChange(false);
              navigate("/courses");
            }}
            onSettings={() => {
              onOpenChange(false);
              onOpenSettings();
            }}
          />
        </CommandList>
      </Command>
    </CommandDialog>
  );
}

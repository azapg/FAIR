import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { COURSE_ICON_OPTIONS, CourseIcon, getCourseIconOption } from "@/app/courses/course-icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

export function CourseIconPicker({
  value,
  onValueChange,
}: {
  value: string;
  onValueChange: (value: string) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = getCourseIconOption(value);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const options = useMemo(
    () => COURSE_ICON_OPTIONS.filter((item) => {
      if (!normalizedQuery) return true;
      const searchText = [t(item.labelKey), item.key, ...item.keywords].join(" ").toLocaleLowerCase();
      return searchText.includes(normalizedQuery);
    }),
    [normalizedQuery, t],
  );

  return (
      <Popover open={open} onOpenChange={(next) => {
        setOpen(next);
        if (!next) setQuery("");
      }}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-9 shrink-0 text-primary"
            aria-label={`${t("courses.chooseIcon")}: ${t(selected.labelKey)}`}
            title={t(selected.labelKey)}
          >
            <CourseIcon iconKey={selected.key} size={20} />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" sideOffset={8} className="w-[min(23rem,calc(100vw-2rem))] overflow-hidden p-0">
          <div className="border-b border-border/70 px-3 pt-3">
            <span className="inline-flex border-b-2 border-foreground px-1 pb-2 text-xs font-medium">
              {t("courses.iconsTab")}
            </span>
          </div>
          <div className="p-2.5">
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                autoFocus
                className="h-8 pl-8"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("courses.searchIcons")}
                aria-label={t("courses.searchIcons")}
              />
            </div>
          </div>
          <div className="px-3 pb-1 text-[0.6875rem] font-medium text-muted-foreground">
            {t("courses.courseIcons")}
          </div>
          <ScrollArea className="h-[min(17rem,45dvh)] px-2.5 pb-2.5">
            {options.length ? (
              <div className="grid grid-cols-8 gap-0.5 pr-2">
                {options.map((item) => {
                  const isSelected = item.key === value;
                  return (
                    <button
                      type="button"
                      key={item.key}
                      aria-pressed={isSelected}
                      aria-label={t(item.labelKey)}
                      title={t(item.labelKey)}
                      className={cn(
                        "grid aspect-square min-w-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/35 focus-visible:outline-none",
                        isSelected && "bg-primary/12 text-primary",
                      )}
                      onClick={() => {
                        onValueChange(item.key);
                        setOpen(false);
                      }}
                    >
                      <CourseIcon iconKey={item.key} size={20} />
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="py-10 text-center text-sm text-muted-foreground">{t("common.noResults")}</p>
            )}
          </ScrollArea>
        </PopoverContent>
      </Popover>
  );
}

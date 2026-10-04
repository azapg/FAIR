import { useEffect, useRef, useState, type ReactNode } from "react";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  barActions?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({
  title,
  description,
  actions,
  barActions,
  children,
}: PageHeaderProps) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setIsCollapsed(!entry.isIntersecting),
      { rootMargin: "-64px 0px 0px 0px", threshold: 0 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <header className="pointer-events-none fixed inset-x-0 top-4 z-40 px-6 sm:px-8 md:hidden">
        <div className="flex items-center gap-2">
          <SidebarTrigger className="pointer-events-auto size-10 shrink-0 rounded-full border-border/70 bg-background/85 shadow-[var(--shadow-button-soft)] backdrop-blur-xl" />
          <div
            className={cn(
              "min-w-0 flex-1 transition-all duration-200",
              isCollapsed
                ? "translate-y-0 opacity-100"
                : "-translate-y-1 pointer-events-none opacity-0",
            )}
            aria-hidden={!isCollapsed}
          >
            <div className="flex h-10 items-center rounded-full border border-border/70 bg-background/85 px-4 shadow-[var(--shadow-button-soft)] backdrop-blur-xl">
              <span className="truncate text-[0.8125rem] leading-4 font-medium">{title}</span>
            </div>
          </div>
          {barActions && (
            <div className="pointer-events-auto flex shrink-0 items-center gap-2">
              {barActions}
            </div>
          )}
        </div>
      </header>
      <div className="mx-auto w-full max-w-[1440px] px-6 pt-16 sm:px-8 sm:pt-14 md:pt-8">
        <div className="flex items-start justify-between gap-5">
          <div className="min-w-0">
            <h1
              ref={titleRef}
              className="text-xl leading-6 font-semibold tracking-[-0.02em] text-balance md:text-[1.625rem] md:leading-8"
            >
              {title}
            </h1>
            {description && (
              <p className="mt-1.5 max-w-2xl text-sm leading-5 text-muted-foreground text-pretty">{description}</p>
            )}
          </div>
          {actions && (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          )}
        </div>
        {children}
      </div>
    </>
  );
}

import { type ComponentProps, type ReactNode } from "react";
import { type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface FloatingNavItem {
  value: string;
  label: string;
  icon: LucideIcon;
}

interface FloatingNavProps {
  items: FloatingNavItem[];
  value: string;
  onValueChange: (value: string) => void;
  action?: ReactNode;
  className?: string;
}

export function FloatingNav({
  items,
  value,
  onValueChange,
  action,
  className,
}: FloatingNavProps) {
  if (items.length === 0 && !action) return null;

  const hasViews = items.length > 0;
  const hasAction = Boolean(action);

  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-4 z-40 flex items-center gap-2 px-6 pb-[env(safe-area-inset-bottom)] md:hidden sm:px-8",
        hasViews && hasAction && "justify-end",
        hasViews && !hasAction && "justify-center",
        !hasViews && hasAction && "justify-end",
        className,
      )}
    >
      {hasViews && (
        <nav
          aria-label="Views"
          className={cn(
            "flex min-w-0 items-center gap-1 rounded-full border bg-background/80 p-1.5 shadow-sm backdrop-blur",
            hasAction ? "flex-1" : "w-full max-w-md",
          )}
        >
          {items.map((item) => {
            const isActive = item.value === value;
            return (
              <button
                key={item.value}
                type="button"
                aria-label={item.label}
                title={item.label}
                aria-current={isActive ? "page" : undefined}
                onClick={() => onValueChange(item.value)}
                className={cn(
                  "flex h-10 min-w-0 flex-1 basis-0 items-center justify-center rounded-full px-2 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground",
                  isActive && "bg-muted text-foreground hover:bg-muted",
                )}
              >
                <item.icon className="size-5 shrink-0" />
              </button>
            );
          })}
        </nav>
      )}
      {action}
    </div>
  );
}

interface FloatingActionButtonProps extends ComponentProps<typeof Button> {
  icon?: LucideIcon;
}

export function FloatingActionButton({
  icon: Icon,
  children,
  className,
  ...props
}: FloatingActionButtonProps) {
  return (
    <Button
      size="icon"
      className={cn(
        "size-12 shrink-0 rounded-full border bg-background/80 text-foreground shadow-sm backdrop-blur",
        className,
      )}
      {...props}
    >
      {Icon ? <Icon className="size-5" /> : children}
    </Button>
  );
}

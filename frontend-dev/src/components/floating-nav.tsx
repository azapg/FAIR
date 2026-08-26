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

  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-4 z-40 flex items-center justify-center gap-2 px-6 pb-[env(safe-area-inset-bottom)] md:hidden",
        className,
      )}
    >
      {action}
      {items.length > 0 && (
        <nav
          aria-label="Views"
          className="flex items-center gap-1 rounded-full border bg-background/80 p-1.5 shadow-sm backdrop-blur"
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
                  "flex size-10 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground",
                  isActive && "bg-muted text-foreground hover:bg-muted",
                )}
              >
                <item.icon className="size-5" />
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
        "size-12 shrink-0 rounded-full border bg-background/80 shadow-sm backdrop-blur",
        className,
      )}
      {...props}
    >
      {Icon ? <Icon className="size-5" /> : children}
    </Button>
  );
}

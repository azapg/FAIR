import { Info, OctagonAlert, ShieldAlert, Terminal } from "lucide-react";

export function LevelBadge({ level }: { level?: string | null }) {
  if (!level) return null;
  const colors: Record<string, string> = {
    debug: "bg-muted text-muted-foreground",
    info: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    warning:
      "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    error: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300",
  };
  const color = colors[level] || colors.info;
  const Icon =
    level === "error"
      ? OctagonAlert
      : level === "warning"
        ? ShieldAlert
        : level === "debug"
          ? Terminal
          : Info;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${color}`}
    >
      <Icon className="h-3 w-3" />
      {level.toUpperCase()}
    </span>
  );
}

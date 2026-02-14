import { ReactNode } from "react";
import { SessionLog } from "@/store/session-store";
import { LevelBadge } from "@/app/assignment/components/sidebar/logs/level-badge";

type LogCardShellProps = {
  log: SessionLog;
  children: ReactNode;
};

export function LogCardShell({ log, children }: LogCardShellProps) {
  return (
    <div className="rounded-md border p-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 truncate">
          <LevelBadge level={log.level} />
          <span className="text-xs text-muted-foreground">
            {log.payload?.plugin?.name || "System"}
          </span>
        </div>
        {log.ts && (
          <span className="text-[10px] text-muted-foreground">
            {new Date(log.ts).toLocaleTimeString()}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

import {ChevronLeft, Info, OctagonAlert, ShieldAlert, Terminal} from "lucide-react";
import {useEffect, useMemo, useRef} from "react";
import api from "@/lib/api";
import {useSessionStore, SessionLog} from "@/store/session-store";
import {Button} from "@/components/ui/button";
import {Separator} from "@/components/ui/separator";
import { SidebarContent } from "@/components/ui/sidebar";

export function ExecutionLogsView({ onBack }: { onBack: () => void }) {
  const { currentSession, sessionLogs, setLogs } = useSessionStore();

  console.log({sessionLogs})

  useEffect(() => {
    // Backfill from API if we have a session but no logs yet (e.g., page reload)
    const load = async () => {
      if (!currentSession) return;
      if (sessionLogs.length > 0) return;
      try {
        const res = await api.get(`/sessions/${currentSession.id}/logs`);
        setLogs(res.data || []);
      } catch (e) {
        // Silently ignore; live updates will still populate logs
      }
    };
    void load();
  }, [currentSession?.id]);

  const grouped = useMemo(() => sessionLogs, [sessionLogs]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Always follow the latest entry for a smooth, live log reading experience
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [grouped.length]);

  return (
    <SidebarContent className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-2.5">
        <Button size="icon" variant="ghost" onClick={onBack}>
          <ChevronLeft />
        </Button>
        <div className="flex flex-col">
          <span className="font-semibold">Execution Logs</span>
          {currentSession && (
            <span className="text-xs text-muted-foreground">Session {currentSession.id}</span>
          )}
        </div>
      </div>
      <Separator />
      <div className="flex-1 overflow-auto px-2.5 py-3 space-y-2">
        {grouped.length === 0 && (
          <div className="text-sm text-muted-foreground px-2">No logs yet. When a workflow runs, messages will appear here in real time.</div>
        )}
        {grouped.map((log) => (
          <LogRow key={`${log.index}-${log.type}-${log.ts ?? ''}`} log={log} />
        ))}
        <div ref={bottomRef} />
      </div>
    </SidebarContent>
  );
}

function LevelBadge({ level }: { level?: string | null }) {
  if (!level) return null;
  const colors: Record<string, string> = {
    debug: "bg-muted text-muted-foreground",
    info: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    warning: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    error: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300",
  };
  const color = colors[level] || colors.info;
  const Icon = level === 'error' ? OctagonAlert : level === 'warning' ? ShieldAlert : level === 'debug' ? Terminal : Info;
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${color}`}>
      <Icon className="h-3 w-3" />
      {level.toUpperCase()}
    </span>
  );
}

function LogRow({ log }: { log: SessionLog }) {
  if (log.type === 'log') {
    return (
      <div className="rounded-md border p-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <LevelBadge level={log.level} />
            {log.plugin && <span className="text-xs text-muted-foreground">{log.plugin}</span>}
          </div>
          {log.ts && <span className="text-[10px] text-muted-foreground">{new Date(log.ts).toLocaleTimeString()}</span>}
        </div>
        {log.message && <div className="mt-1">{log.message}</div>}
      </div>
    );
  }

  if (log.type === 'update') {
    return (
//       <div className="rounded-md border p-2 text-xs">
//         <div className="flex items-center justify-between">
//           <div className="font-medium">Update{log.object ? `: ${log.object}` : ''}</div>
//           {log.ts && <span className="text-[10px] text-muted-foreground">{new Date(log.ts).toLocaleTimeString()}</span>}
//         </div>
//         <pre className="mt-1 overflow-auto rounded bg-muted p-2 text-[11px] leading-tight">
// {JSON.stringify(log.payload, null, 2)}
//         </pre>
//       </div>
    <></>
    );
  }

  if (log.type === 'close') {
    return (
      <div className="rounded-md border border-green-500/40 bg-green-500/5 p-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="font-medium">Session closed</div>
          {log.ts && <span className="text-[10px] text-muted-foreground">{new Date(log.ts).toLocaleTimeString()}</span>}
        </div>
        {log.payload?.reason && <div className="mt-1 text-xs text-muted-foreground">{log.payload.reason}</div>}
      </div>
    );
  }

  // Fallback
  return (
    <div className="rounded-md border p-2 text-xs">
      <div className="font-medium">{log.type}</div>
      <pre className="mt-1 overflow-auto rounded bg-muted p-2 text-[11px] leading-tight">
{JSON.stringify(log.payload ?? {}, null, 2)}
      </pre>
    </div>
  );
}

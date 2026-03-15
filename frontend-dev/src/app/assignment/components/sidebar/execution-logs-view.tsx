import { ChevronLeft } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import api from "@/lib/api";
import { useSessionStore } from "@/store/session-store";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarContent } from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { LogRow } from "@/app/assignment/components/sidebar/logs/log-row";

export function ExecutionLogsView({ onBack }: { onBack: () => void }) {
  const { currentSession, sessionLogs, setLogs } = useSessionStore();

  useEffect(() => {
    // Backfill from API if we have a session but no logs yet (e.g., page reload)
    const load = async () => {
      if (!currentSession) return;
      if (sessionLogs.length > 0) return;
      try {
        const res = await api.get(`/workflow-runs/${currentSession.id}`);
        setLogs(res.data?.logs?.history || []);
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
            <span className="text-xs text-muted-foreground">
              Session {currentSession.id}
            </span>
          )}
        </div>
      </div>
      <Separator />
      <div className="flex-1 overflow-auto">
        <ScrollArea className="h-full p-3">
          {grouped.length === 0 && (
            <div className="text-sm text-muted-foreground px-2">
              No logs yet. When a workflow runs, messages will appear here in
              real time.
            </div>
          )}
          <div className="flex flex-col gap-3">
            {grouped.map((log) => (
              <LogRow
                key={`${log.index}-${log.type}-${log.ts ?? ""}`}
                log={log}
              />
            ))}
          </div>
          <div ref={bottomRef} />
        </ScrollArea>
      </div>
    </SidebarContent>
  );
}

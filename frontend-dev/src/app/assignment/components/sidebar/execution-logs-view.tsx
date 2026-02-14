import {
  ChevronLeft,
  Info,
  OctagonAlert,
  ShieldAlert,
  Terminal,
  Filter,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import { useSessionStore, SessionLog } from "@/store/session-store";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarContent } from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";

export function ExecutionLogsView({ onBack }: { onBack: () => void }) {
  const { currentSession, sessionLogs, setLogs } = useSessionStore();
  const [showFilters, setShowFilters] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState<string | null>(null);
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null);

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

  // Get unique levels and plugins for filtering
  const availableLevels = useMemo(() => {
    const levels = new Set(sessionLogs.map(log => log.level).filter(Boolean));
    return Array.from(levels) as string[];
  }, [sessionLogs]);

  const availablePlugins = useMemo(() => {
    const plugins = new Set(sessionLogs.map(log => log.plugin).filter(Boolean));
    return Array.from(plugins) as string[];
  }, [sessionLogs]);

  // Filter logs based on selected filters
  const filteredLogs = useMemo(() => {
    return sessionLogs.filter(log => {
      if (selectedLevel && log.level !== selectedLevel) return false;
      if (selectedPlugin && log.plugin !== selectedPlugin) return false;
      return true;
    });
  }, [sessionLogs, selectedLevel, selectedPlugin]);

  const grouped = useMemo(() => filteredLogs, [filteredLogs]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Always follow the latest entry for a smooth, live log reading experience
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [grouped.length]);

  const clearFilters = () => {
    setSelectedLevel(null);
    setSelectedPlugin(null);
  };

  const hasActiveFilters = selectedLevel || selectedPlugin;

  return (
    <SidebarContent className="flex flex-col h-full">
      {/* Improved Header */}
      <div className="flex items-center gap-2 p-3">
        <Button size="icon" variant="ghost" onClick={onBack}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="font-semibold text-sm">Execution Logs</span>
          {currentSession && (
            <span className="text-xs text-muted-foreground truncate">
              Session {currentSession.id}
            </span>
          )}
        </div>
        <Button
          size="icon"
          variant="ghost"
          onClick={() => setShowFilters(!showFilters)}
          className="h-8 w-8"
        >
          <Filter className="h-4 w-4" />
        </Button>
      </div>

      {/* Filters Section */}
      {showFilters && (
        <div className="px-3 pb-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Filters</span>
            {hasActiveFilters && (
              <Button
                size="icon"
                variant="ghost"
                onClick={clearFilters}
                className="h-6 w-6"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
          
          {/* Level Filters */}
          {availableLevels.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Level:</span>
              <div className="flex flex-wrap gap-1">
                <Badge
                  variant={!selectedLevel ? "default" : "outline"}
                  className="cursor-pointer text-[10px] px-2 py-0.5"
                  onClick={() => setSelectedLevel(null)}
                >
                  All
                </Badge>
                {availableLevels.map(level => (
                  <Badge
                    key={level}
                    variant={selectedLevel === level ? "default" : "outline"}
                    className="cursor-pointer text-[10px] px-2 py-0.5"
                    onClick={() => setSelectedLevel(level)}
                  >
                    {level.toUpperCase()}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Plugin Filters */}
          {availablePlugins.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Plugin:</span>
              <div className="flex flex-wrap gap-1">
                <Badge
                  variant={!selectedPlugin ? "default" : "outline"}
                  className="cursor-pointer text-[10px] px-2 py-0.5"
                  onClick={() => setSelectedPlugin(null)}
                >
                  All
                </Badge>
                {availablePlugins.map(plugin => (
                  <Badge
                    key={plugin}
                    variant={selectedPlugin === plugin ? "default" : "outline"}
                    className="cursor-pointer text-[10px] px-2 py-0.5"
                    onClick={() => setSelectedPlugin(plugin)}
                  >
                    {plugin}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Active Filters Summary */}
          {hasActiveFilters && (
            <div className="text-xs text-muted-foreground">
              Showing {filteredLogs.length} of {sessionLogs.length} logs
            </div>
          )}
        </div>
      )}
      
      <Separator />
      
      {/* Logs Content */}
      <div className="flex-1 overflow-auto px-3 py-3 space-y-2">
        {filteredLogs.length === 0 && (
          <div className="text-sm text-muted-foreground px-2">
            {hasActiveFilters 
              ? "No logs match the selected filters." 
              : "No logs yet. When a workflow runs, messages will appear here in real time."
            }
          </div>
        )}
        {filteredLogs.map((log) => (
          <LogRow key={`${log.index}-${log.type}-${log.ts ?? ""}`} log={log} />
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

function LogRow({ log }: { log: SessionLog }) {
  if (log.type === "log") {
    return (
      <div className="rounded-md border p-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <LevelBadge level={log.level} />
            {log.plugin && (
              <span className="text-xs text-muted-foreground">
                {log.plugin}
              </span>
            )}
          </div>
          {log.ts && (
            <span className="text-[10px] text-muted-foreground">
              {new Date(log.ts).toLocaleTimeString()}
            </span>
          )}
        </div>
        {log.message && <div className="mt-1">{log.message}</div>}
      </div>
    );
  }

  if (log.type === "update") {
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

  if (log.type === "close") {
    return (
      <div className="rounded-md border border-green-500/40 bg-green-500/5 p-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="font-medium">Session closed</div>
          {log.ts && (
            <span className="text-[10px] text-muted-foreground">
              {new Date(log.ts).toLocaleTimeString()}
            </span>
          )}
        </div>
        {log.payload?.reason && (
          <div className="mt-1 text-xs text-muted-foreground">
            {log.payload.reason}
          </div>
        )}
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

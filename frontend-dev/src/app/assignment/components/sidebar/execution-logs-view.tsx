import {
  ChevronLeft,
  Info,
  OctagonAlert,
  ShieldAlert,
  Terminal,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import { useSessionStore, SessionLog } from "@/store/session-store";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { SidebarContent } from "@/components/ui/sidebar";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

export function ExecutionLogsView({ onBack }: { onBack: () => void }) {
  const { currentSession, sessionLogs, setLogs } = useSessionStore();

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
  if (log.type === "log" || log.type === "system") {
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
        {log.payload?.message && <div className="mt-1 break-words">{log.payload.message}</div>}
      </div>
    );
  }

  if (log.type === "image") {
    const image = log.payload?.image;
    if (!image?.src || !image?.alt) return null;

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
        {log.payload?.description && (
          <div className="mt-1 break-words">{log.payload.description}</div>
        )}
        <div className="mt-2">
          <ImageWithFallback src={image.src} alt={image.alt} />
        </div>
      </div>
    );
  }

  if (log.type === "image_group") {
    const images = (log.payload?.images || []).filter((img) => img?.src && img?.alt);
    if (images.length === 0) return null;

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
        {log.payload?.description && (
          <div className="mt-1 break-words">{log.payload.description}</div>
        )}
        <ScrollArea className="mt-2 w-full whitespace-nowrap">
          <div className="flex gap-3 pb-2">
            {images.map((image, idx) => (
              <div key={`${log.index}-img-${idx}`} className="w-56 shrink-0">
                <ImageWithFallback src={image.src!} alt={image.alt!} />
              </div>
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </div>
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

  console.warn("Unknown log type:", log);
  return null;
}

function ImageWithFallback({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  if (failed) {
    return (
      <div className="rounded border bg-muted/40 px-2 py-1 text-xs text-muted-foreground">
        {alt}
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full cursor-zoom-in"
      >
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className="max-h-64 w-full rounded border object-contain"
        />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          showCloseButton={true}
          className="max-h-[90vh] max-w-[90vw] p-3 sm:max-w-[90vw]"
        >
          <DialogTitle className="sr-only">{alt}</DialogTitle>
          <div className="flex items-center justify-center">
            <img
              src={src}
              alt={alt}
              className="max-h-[82vh] w-auto max-w-full rounded object-contain"
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

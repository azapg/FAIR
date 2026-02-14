import { SessionLog } from "@/store/session-store";

export function RenderLogClose({ log }: { log: SessionLog }) {
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

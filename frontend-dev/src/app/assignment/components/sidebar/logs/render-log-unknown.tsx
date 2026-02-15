import { SessionLog } from "@/store/session-store";

export function RenderLogUnknown({ log }: { log: SessionLog }) {
  console.warn("Unknown log type:", log);
  return (
    <div className="rounded-md border border-dashed p-2 text-xs text-muted-foreground">
      Unsupported log type: {log.type}
    </div>
  );
}

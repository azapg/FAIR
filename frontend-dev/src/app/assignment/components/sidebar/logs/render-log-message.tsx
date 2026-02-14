import { SessionLog } from "@/store/session-store";
import { LogCardShell } from "@/app/assignment/components/sidebar/logs/log-card-shell";

export function RenderLogMessage({ log }: { log: SessionLog }) {
  return (
    <LogCardShell log={log}>
      {log.payload?.message && (
        <div className="mt-1 break-words">{log.payload.message}</div>
      )}
    </LogCardShell>
  );
}

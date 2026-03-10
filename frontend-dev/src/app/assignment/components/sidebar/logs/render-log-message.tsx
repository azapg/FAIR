import { SessionLog } from "@/store/session-store";
import { LogCardShell } from "@/app/assignment/components/sidebar/logs/log-card-shell";

export function RenderLogMessage({ log }: { log: SessionLog }) {
  const message =
    log.payload?.message ||
    log.payload?.output ||
    log.payload?.error ||
    (typeof log.payload?.percent === "number"
      ? `Progress ${log.payload.percent}%`
      : undefined) ||
    (log.type === "result" ? "Step completed" : undefined);

  return (
    <LogCardShell log={log}>
      {message && <div className="mt-1 break-words">{message}</div>}
    </LogCardShell>
  );
}

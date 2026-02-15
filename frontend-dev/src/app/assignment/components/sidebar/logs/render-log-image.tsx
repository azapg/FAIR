import { SessionLog } from "@/store/session-store";
import { LogCardShell } from "@/app/assignment/components/sidebar/logs/log-card-shell";
import { ImageWithFallback } from "@/app/assignment/components/sidebar/logs/image-with-fallback";

export function RenderLogImage({ log }: { log: SessionLog }) {
  const image = log.payload?.image;
  if (!image?.src || !image?.alt) return null;

  return (
    <LogCardShell log={log}>
      {log.payload?.description && (
        <div className="mt-1 break-words">{log.payload.description}</div>
      )}
      <div className="mt-2">
        <ImageWithFallback src={image.src} alt={image.alt} />
      </div>
    </LogCardShell>
  );
}

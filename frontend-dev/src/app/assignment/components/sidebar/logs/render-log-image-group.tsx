import { SessionLog } from "@/store/session-store";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { LogCardShell } from "@/app/assignment/components/sidebar/logs/log-card-shell";
import { ImageWithFallback } from "@/app/assignment/components/sidebar/logs/image-with-fallback";

export function RenderLogImageGroup({ log }: { log: SessionLog }) {
  const images = (log.payload?.images || []).filter((img) => img?.src && img?.alt);
  if (images.length === 0) return null;

  return (
    <LogCardShell log={log}>
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
    </LogCardShell>
  );
}

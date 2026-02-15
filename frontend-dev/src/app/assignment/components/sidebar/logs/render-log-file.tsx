import { useMemo, useState } from "react";
import { FileText } from "lucide-react";
import { SessionLog } from "@/store/session-store";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { LogCardShell } from "@/app/assignment/components/sidebar/logs/log-card-shell";

function formatBytes(sizeBytes?: number): string {
  if (!sizeBytes || sizeBytes < 0) return "0 B";
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function RenderLogFile({ log }: { log: SessionLog }) {
  const [open, setOpen] = useState(false);
  const file = log.payload?.file;
  const name = file?.name;
  const content = file?.content;
  if (!name || !content) return null;

  const fileType = useMemo(() => {
    if (file?.file_type === "markdown") return "markdown";
    return "text";
  }, [file?.file_type]);

  const fileBadge = fileType === "markdown" ? "MARKDOWN" : "TEXT";

  return (
    <LogCardShell log={log}>
      {log.payload?.description && (
        <div className="mt-1 break-words">{log.payload.description}</div>
      )}
      <div className="mt-2 rounded border bg-muted/30 p-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-xs font-medium">{name}</span>
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {fileBadge}
            </span>
          </div>
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
            Open
          </Button>
        </div>
        <div className="mt-1 text-[10px] text-muted-foreground">
          {formatBytes(file?.size_bytes)}
          {file?.encoding ? `  •  ${file.encoding}` : ""}
          {file?.language ? `  •  ${file.language}` : ""}
        </div>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          showCloseButton={true}
          className="max-h-[90vh] max-w-[90vw] p-3 sm:max-w-[90vw]"
        >
          <DialogTitle className="text-sm font-semibold">{name}</DialogTitle>
          <div className="max-h-[78vh] overflow-auto rounded border p-3">
            {fileType === "markdown" ? (
              <MarkdownRenderer className="text-sm">{content}</MarkdownRenderer>
            ) : (
              <pre className="whitespace-pre-wrap break-words text-xs">{content}</pre>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </LogCardShell>
  );
}

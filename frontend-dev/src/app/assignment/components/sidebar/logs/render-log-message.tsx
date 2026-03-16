import { useState } from "react";
import { ChevronDown, ChevronUp, Copy, TriangleAlert } from "lucide-react";
import { SessionLog } from "@/store/session-store";
import { LogCardShell } from "@/app/assignment/components/sidebar/logs/log-card-shell";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";

export function RenderLogMessage({ log }: { log: SessionLog }) {
  const [isOpen, setIsOpen] = useState(false);

  const message =
    log.payload?.message ||
    log.payload?.output ||
    log.payload?.error ||
    (typeof log.payload?.percent === "number"
      ? `Progress ${log.payload.percent}%`
      : undefined) ||
    (log.type === "result" ? "Step completed" : undefined);

  const traceback = log.payload?.traceback;

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (traceback) {
      await navigator.clipboard.writeText(traceback);
    }
  };

  if (traceback) {
    return (
      <LogCardShell log={log}>
        <Collapsible
          open={isOpen}
          onOpenChange={setIsOpen}
          className="mt-2 overflow-hidden rounded-md border border-border bg-muted/50 font-mono text-sm shadow-sm"
        >
          <div
            className="flex items-start justify-between border-b border-transparent px-3 py-2.5 transition-colors data-[state=open]:border-border"
            data-state={isOpen ? "open" : "closed"}
          >
            <div className="flex min-w-0 flex-1 items-start gap-2.5">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" strokeWidth={2} />
              <div className="min-w-0 flex-1 break-all font-medium text-destructive">
                {message || "Error"}
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0 ml-3">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={handleCopy}
                title="Copy traceback"
              >
                <Copy className="h-3.5 w-3.5" />
              </Button>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  {isOpen ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
          <CollapsibleContent>
            <ScrollArea className="max-h-[400px] w-full">
              <div className="min-w-full w-max p-3 leading-relaxed text-muted-foreground">
                <pre className="font-mono">{traceback}</pre>
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      </LogCardShell>
    );
  }

  return (
    <LogCardShell log={log}>
      {message && <div className="mt-1 break-words">{message}</div>}
    </LogCardShell>
  );
}
import {
  useMemo,
  useState,
  type ReactNode,
  type ComponentProps,
  type ComponentType,
} from "react";
import { ArrowUpRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Artifact } from "@/hooks/use-artifacts";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { MarkdownRenderer } from "@/components/markdown-renderer";

type ArtifactActionProps = Omit<ComponentProps<typeof Button>, "onClick"> & {
  artifact: Artifact;
  icon?: ComponentType<{ className?: string; size?: number }>;
  label?: ReactNode;
};

const isTextLike = (mime?: string) => {
  if (!mime) return false;
  return (
    mime.startsWith("text/") ||
    mime.includes("markdown") ||
    mime === "application/json"
  );
};

const isMarkdown = (mime?: string) => Boolean(mime && mime.includes("markdown"));

const shouldOpenInNewTab = (mime?: string) =>
  Boolean(mime && (mime.startsWith("image/") || mime === "application/pdf"));

const parseFilename = (disposition?: string, fallback?: string) => {
  if (!disposition) return fallback;
  const match = disposition.match(/filename="?([^\";]+)"?/i);
  return match?.[1] ?? fallback;
};

export function ArtifactAction({
  artifact,
  icon: Icon,
  label,
  ...buttonProps
}: ArtifactActionProps) {
  const [open, setOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);

  const previewMode = useMemo(
    () => (isMarkdown(artifact.mime) ? "markdown" : "text"),
    [artifact.mime],
  );
  const isPreviewable = useMemo(
    () => isTextLike(artifact.mime),
    [artifact.mime],
  );

  const handleAction = async () => {
    const revokeUrl = (url: string) =>
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);

    setIsLoading(true);
    try {
      const response = await api.get(`/artifacts/${artifact.id}/download`, {
        responseType: "blob",
      });

      const blob = response.data as Blob;
      const filename = parseFilename(
        response.headers?.["content-disposition"],
        artifact.title || "artifact",
      );

      if (isPreviewable) {
        const text = await blob.text();
        setPreviewContent(text);
        setOpen(true);
        return;
      }

      const objectUrl = URL.createObjectURL(blob);
      if (shouldOpenInNewTab(artifact.mime)) {
        window.open(objectUrl, "_blank", "noopener,noreferrer");
        revokeUrl(objectUrl);
        return;
      }

      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename || "artifact";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      document.body.appendChild(link);
      link.click();
      link.remove();
      revokeUrl(objectUrl);
    } catch (error) {
      const description = error instanceof Error ? error.message : undefined;
      toast.error("Unable to open artifact", { description });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Button onClick={handleAction} {...buttonProps} disabled={isLoading || buttonProps.disabled}>
        {Icon ? <Icon className="h-4 w-4" /> : null}
        {label ?? artifact.title}
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
        )}
      </Button>

      {isPreviewable ? (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent showCloseButton className="max-h-[90vh] max-w-[90vw] p-3">
            <DialogTitle className="text-sm font-semibold">
              {artifact.title}
            </DialogTitle>
            <div className="max-h-[75vh] overflow-auto rounded border p-3">
              {previewMode === "markdown" ? (
                <MarkdownRenderer className="text-sm">
                  {previewContent}
                </MarkdownRenderer>
              ) : (
                <pre className="whitespace-pre-wrap break-words text-xs">
                  {previewContent}
                </pre>
              )}
            </div>
          </DialogContent>
        </Dialog>
      ) : null}
    </>
  );
}

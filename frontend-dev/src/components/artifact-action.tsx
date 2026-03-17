import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
  type ComponentProps,
  type ComponentType,
} from "react";
import { ArrowUpRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Artifact } from "@/hooks/use-artifacts";
import api, { getApiBaseUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { PdfPreview } from "@/components/pdf-preview";
import { ScrollArea } from "@/components/ui/scroll-area";

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

const isPdf = (mime?: string) => mime === "application/pdf";

const shouldOpenInNewTab = (mime?: string) =>
  Boolean(mime && mime.startsWith("image/"));

const isSameOrigin = (url: string) => {
  try {
    return new URL(url, window.location.href).origin === window.location.origin;
  } catch (error) {
    return false;
  }
};

const resolveDownloadUrl = (url: string) => {
  try {
    return new URL(url, getApiBaseUrl()).toString();
  } catch (error) {
    return url;
  }
};

const isApiOrigin = (url: string) => {
  try {
    const apiOrigin = new URL(getApiBaseUrl(), window.location.origin).origin;
    return new URL(url, window.location.href).origin === apiOrigin;
  } catch (error) {
    return false;
  }
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
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const previewMode = useMemo(
    () => (isMarkdown(artifact.mime) ? "markdown" : "text"),
    [artifact.mime],
  );
  const isPreviewable = useMemo(
    () => isTextLike(artifact.mime),
    [artifact.mime],
  );

  const isPdfArtifact = useMemo(() => isPdf(artifact.mime), [artifact.mime]);

  useEffect(() => {
    return () => {
      if (pdfUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const handlePdfClose = (nextOpen: boolean) => {
    setPdfOpen(nextOpen);
    if (!nextOpen && pdfUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(pdfUrl);
      setPdfUrl(null);
    }
  };

  const handleAction = async () => {
    setIsLoading(true);
    try {
      const response = await api.get(`/artifacts/${artifact.id}/download`, {
        responseType: "json",
        headers: {
          Accept: "application/json",
        },
      });

      const rawUrl = (response.data as { url?: string })?.url;
      const url = rawUrl ? resolveDownloadUrl(rawUrl) : undefined;
      if (!url) {
        throw new Error("Missing download URL");
      }

      if (isPreviewable) {
        if (isApiOrigin(url)) {
          const textResponse = await api.get(url, { responseType: "text" });
          setPreviewContent(textResponse.data);
          setOpen(true);
          return;
        }
        if (isSameOrigin(url)) {
          const textResponse = await api.get(url, { responseType: "text" });
          setPreviewContent(textResponse.data);
          setOpen(true);
          return;
        }
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }

      if (isPdfArtifact) {
        let resolvedUrl = url;
        if (isApiOrigin(url) || isSameOrigin(url)) {
          const fileResponse = await api.get(url, { responseType: "blob" });
          resolvedUrl = URL.createObjectURL(fileResponse.data);
        }
        setPdfUrl(resolvedUrl);
        setPdfOpen(true);
        return;
      }

      if (shouldOpenInNewTab(artifact.mime)) {
        if (isApiOrigin(url)) {
          const fileResponse = await api.get(url, { responseType: "blob" });
          const objectUrl = URL.createObjectURL(fileResponse.data);
          window.open(objectUrl, "_blank", "noopener,noreferrer");
          return;
        }
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }

      if (isApiOrigin(url)) {
        const fileResponse = await api.get(url, { responseType: "blob" });
        const objectUrl = URL.createObjectURL(fileResponse.data);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = artifact.title || "artifact";
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
        return;
      }

      const link = document.createElement("a");
      link.href = url;
      link.download = artifact.title || "artifact";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      document.body.appendChild(link);
      link.click();
      link.remove();
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
          <DialogContent showCloseButton className="flex h-[95vh] w-[95vw] max-w-7xl flex-col p-3 sm:max-w-7xl">
            <DialogTitle className="text-sm font-semibold">
              {artifact.title}
            </DialogTitle>
            <div className="flex-1 overflow-auto rounded border p-3">
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

      {isPdfArtifact ? (
        <Dialog open={pdfOpen} onOpenChange={handlePdfClose}>
          <DialogContent showCloseButton className="flex h-[95vh] w-[95vw] max-w-7xl flex-col p-3 sm:max-w-7xl">
            <DialogTitle className="text-sm font-semibold">
              {artifact.title}
            </DialogTitle>
            <div className="mb-2 flex items-center justify-end">
              {pdfUrl ? (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => window.open(pdfUrl, "_blank", "noopener,noreferrer")}
                >
                  Open in new tab
                </Button>
              ) : null}
            </div>
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4">
                {pdfUrl ? <PdfPreview url={pdfUrl} /> : null}
              </div>
            </ScrollArea>
          </DialogContent>
        </Dialog>
      ) : null}
    </>
  );
}

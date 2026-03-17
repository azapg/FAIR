import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf";
import workerSrc from "pdfjs-dist/legacy/build/pdf.worker?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

type PdfPreviewProps = {
  url: string;
};

export function PdfPreview({ url }: PdfPreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    container.innerHTML = "";
    setIsLoading(true);
    setError(null);

    const loadingTask = pdfjsLib.getDocument(url);

    loadingTask.promise
      .then(async (doc) => {
        for (let pageNumber = 1; pageNumber <= doc.numPages; pageNumber += 1) {
          if (cancelled) break;
          const page = await doc.getPage(pageNumber);
          if (cancelled) {
            page.cleanup();
            break;
          }

          const viewport = page.getViewport({ scale: 2.5 });
          const canvas = document.createElement("canvas");
          const context = canvas.getContext("2d");
          if (!context) {
            page.cleanup();
            continue;
          }

          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.className =
            "mx-auto mb-4 w-full max-w-5xl h-auto rounded-md";

          const renderTask = page.render({ canvasContext: context, viewport });
          await renderTask.promise;
          container.appendChild(canvas);
          page.cleanup();
        }
        if (!cancelled) {
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load PDF");
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
      loadingTask.destroy();
      if (container) {
        container.innerHTML = "";
      }
    };
  }, [url]);

  return (
    <div className="relative">
      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading PDF…</div>
      ) : null}
      {error ? (
        <div className="text-sm text-destructive">{error}</div>
      ) : null}
      <div ref={containerRef} />
    </div>
  );
}

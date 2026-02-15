import { useState } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

export function ImageWithFallback({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  if (failed) {
    return (
      <div className="rounded border bg-muted/40 px-2 py-1 text-xs text-muted-foreground">
        {alt}
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full cursor-zoom-in"
      >
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className="max-h-64 w-full rounded border object-contain"
        />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          showCloseButton={true}
          className="max-h-[90vh] max-w-[90vw] p-3 sm:max-w-[90vw]"
        >
          <DialogTitle className="sr-only">{alt}</DialogTitle>
          <div className="flex items-center justify-center">
            <img
              src={src}
              alt={alt}
              className="max-h-[82vh] w-auto max-w-full rounded object-contain"
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

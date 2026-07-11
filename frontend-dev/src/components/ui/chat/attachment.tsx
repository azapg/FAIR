import * as React from "react"
import { cn } from "@/lib/utils"
import { FileText, Image as ImageIcon, Download, X, AlertCircle, FileSpreadsheet, FileCode } from "lucide-react"

export interface AttachmentProps extends React.ComponentProps<"div"> {
  name: string
  size?: string
  type?: string
  progress?: number // 0 to 100
  error?: string
  onDownload?: () => void
  onRemove?: () => void
  isImage?: boolean
  src?: string
}

export const Attachment = React.forwardRef<HTMLDivElement, AttachmentProps>(
  (
    {
      className,
      name,
      size,
      type,
      progress,
      error,
      onDownload,
      onRemove,
      isImage,
      src,
      ...props
    },
    ref
  ) => {
    const isUploading = progress !== undefined && progress >= 0 && progress < 100

    // Determine the icon
    const getIcon = () => {
      if (isImage) return <ImageIcon className="w-5 h-5 opacity-70" />
      const ext = name.split(".").pop()?.toLowerCase()
      if (ext === "csv" || ext === "xlsx" || ext === "xls") {
        return <FileSpreadsheet className="w-5 h-5 text-emerald-500 opacity-80" />
      }
      if (ext === "json" || ext === "ts" || ext === "tsx" || ext === "py" || ext === "js") {
        return <FileCode className="w-5 h-5 text-amber-500 opacity-80" />
      }
      return <FileText className="w-5 h-5 text-blue-500 opacity-80" />
    }

    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center justify-between p-3 border border-border/80 rounded-xl bg-card hover:bg-muted/30 transition-all select-none w-full max-w-sm relative overflow-hidden group shadow-xs",
          error && "border-destructive/30 bg-destructive/5",
          className
        )}
        {...props}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {/* File Thumbnail or Icon */}
          {isImage && src && !isUploading && !error ? (
            <div className="w-10 h-10 rounded-lg overflow-hidden border border-border/50 shrink-0 bg-muted">
              <img src={src} alt={name} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center bg-muted/40 rounded-lg text-muted-foreground border border-border/50 shrink-0">
              {error ? (
                <AlertCircle className="w-5 h-5 text-destructive" />
              ) : (
                getIcon()
              )}
            </div>
          )}

          {/* Details */}
          <div className="min-w-0 flex-1">
            <h5 className="font-semibold text-foreground text-xs truncate leading-snug">
              {name}
            </h5>
            <div className="flex items-center gap-1.5 mt-0.5">
              {size && (
                <span className="text-muted-foreground text-[10px] font-medium tracking-wide">
                  {size}
                </span>
              )}
              {type && !error && (
                <>
                  <span className="text-muted-foreground/30 text-[9px] font-bold">•</span>
                  <span className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">
                    {type}
                  </span>
                </>
              )}
              {error && (
                <span className="text-destructive text-[10px] font-semibold">
                  {error}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0 z-10 ml-2">
          {onDownload && !isUploading && !error && (
            <button
              type="button"
              onClick={onDownload}
              className="p-1.5 hover:bg-background rounded-lg border border-border/80 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="Download File"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
          )}
          {onRemove && (
            <button
              type="button"
              onClick={onRemove}
              className="p-1.5 hover:bg-background rounded-lg border border-border/80 text-muted-foreground hover:text-destructive transition-colors cursor-pointer"
              title="Remove File"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Progress Bar overlay */}
        {isUploading && (
          <div className="absolute bottom-0 inset-x-0 h-1 bg-muted">
            <div
              className="h-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
    )
  }
)
Attachment.displayName = "Attachment"

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { FileText, Image, Video, Mic, File } from "lucide-react"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getIconForMime(mime: string) {
  if (mime.startsWith('image/')) return Image;
  if (mime.startsWith('video/')) return Video;
  if (mime.startsWith('audio/')) return Mic;
  if (mime === 'application/pdf') return FileText;
  if (mime.startsWith('text/')) return FileText;
  return File;
}

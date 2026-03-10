import { SessionLog } from "@/store/session-store";
import { RenderLogMessage } from "@/app/assignment/components/sidebar/logs/render-log-message";
import { RenderLogImage } from "@/app/assignment/components/sidebar/logs/render-log-image";
import { RenderLogImageGroup } from "@/app/assignment/components/sidebar/logs/render-log-image-group";
import { RenderLogFile } from "@/app/assignment/components/sidebar/logs/render-log-file";
import { RenderLogClose } from "@/app/assignment/components/sidebar/logs/render-log-close";
import { RenderLogUnknown } from "@/app/assignment/components/sidebar/logs/render-log-unknown";

export function LogRow({ log }: { log: SessionLog }) {
  switch (log.type) {
    case "log":
    case "system":
    case "error":
    case "progress":
    case "result":
      return <RenderLogMessage log={log} />;
    case "image":
      return <RenderLogImage log={log} />;
    case "image_group":
      return <RenderLogImageGroup log={log} />;
    case "file":
      return <RenderLogFile log={log} />;
    case "close":
      return <RenderLogClose log={log} />;
    case "update":
      return <></>;
    default:
      return <RenderLogUnknown log={log} />;
  }
}

import { useQueryClient } from "@tanstack/react-query";
import { ReactNode, useEffect, useRef } from "react";
import { useSessionStore } from "@/store/session-store";
import { submissionsKeys } from "@/hooks/use-submissions";
import api from "@/lib/api";

export function SessionSocketProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const {
    currentSession,
    setSocket,
    setCurrentSession,
    addLog,
    clearLogs,
  } = useSessionStore();
  const lastSessionId = useRef<string | null>(null);

  useEffect(() => {
    if (!currentSession) {
      return;
    }

    // New session: proactively clear any stale logs before connecting
    clearLogs();
    const baseUrl = (api.defaults.baseURL || "").replace(/\/$/, "");
    const token =
      typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const streamUrl = token
      ? `${baseUrl}/workflow-runs/${currentSession.id}/stream?access_token=${encodeURIComponent(token)}`
      : `${baseUrl}/workflow-runs/${currentSession.id}/stream`;
    const source = new EventSource(streamUrl, { withCredentials: true });
    setSocket((source as unknown) as WebSocket);
    lastSessionId.current = currentSession.id;

    const handleEvent = (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      addLog(data);
      if (data.type === "update" && data?.payload?.object === "submissions") {
        queryClient.invalidateQueries({
          queryKey: submissionsKeys.lists(),
          refetchType: "active",
        }).then();
      }
      if (data.type === "close") {
        source.close();
        setSocket(null);
        setCurrentSession(null);
      }
    };
    ["log", "progress", "result", "error", "close", "update"].forEach((name) => {
      source.addEventListener(name, handleEvent as EventListener);
    });
    source.addEventListener("end", () => {
      source.close();
      setSocket(null);
      setCurrentSession(null);
    });
    source.onerror = () => {
      source.close();
      setSocket(null);
      setCurrentSession(null);
    };

    return () => {
      source.close();
    };
  }, [currentSession?.id]);

  return <>{children}</>;
}

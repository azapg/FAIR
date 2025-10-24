import { useQueryClient } from "@tanstack/react-query";
import { ReactNode, useEffect, useRef } from "react";
import { useSessionStore } from "@/store/session-store";
import { submissionsKeys } from "@/hooks/use-submissions";

function shapeIncomingLog(data: any) {
  // Accept both normalized messages (with payload) and raw ones (e.g., close reason at root)
  let payload = typeof data?.payload === 'object' ? data.payload : undefined;
  const type = data?.type ?? 'event';
  if (!payload) {
    // For non-log events like 'close', include the original message so UI can read fields like 'reason'
    payload = data && typeof data === 'object' ? { ...data } : { raw: String(data) };
  }
  const plugin = payload?.plugin ?? null;
  const message = payload?.message ?? (type === 'close' && typeof payload?.reason === 'string' ? payload.reason : null);
  return {
    index: typeof data?.index === 'number' ? data.index : -1,
    type,
    ts: data?.ts ?? null,
    level: data?.level ?? null,
    plugin,
    message,
    object: data?.object ?? null,
    payload,
  };
}

export function SessionSocketProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { socket, currentSession, setSocket, setCurrentSession, addLog, clearLogs } =
    useSessionStore();
  const lastSessionId = useRef<string | null>(null);

  useEffect(() => {
    if (!currentSession) {
      if (socket) {
        socket.close();
        setSocket(null);
      }
      return;
    }

    if (socket && lastSessionId.current === currentSession.id) {
      return;
    }

  // New session: proactively clear any stale logs before connecting
  clearLogs();

  const wsUrl = `ws://localhost:8000/api/sessions/${currentSession.id}`;
    const newSocket = new WebSocket(wsUrl);
    setSocket(newSocket);

    newSocket.onopen = () => {
      lastSessionId.current = currentSession.id;
      clearLogs();
    };

    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data)
      // Normalize and store every event for the logs view
      try {
        addLog(shapeIncomingLog(data));
      } catch (e) {
        // noop
      }

      if (data.type == "close") {
        newSocket.close();
        setSocket(null);
        setCurrentSession(null);
        return;
      }

      if (data.type == "update") {
        switch (data.object) {
          case "submissions":
            queryClient
              .invalidateQueries({
                queryKey: submissionsKeys.lists(),
                refetchType: "active",
              })
              .then();
            break;
          default:
            break;
        }
      }
    };

    newSocket.onclose = () => {
      setSocket(null);
    };

    newSocket.onerror = () => {
      newSocket.close();
    };

    return () => {
      if (
        newSocket.readyState === WebSocket.OPEN ||
        newSocket.readyState === WebSocket.CONNECTING
      ) {
        newSocket.close();
      }
    };
  }, [currentSession?.id]);

  return <>{children}</>;
}

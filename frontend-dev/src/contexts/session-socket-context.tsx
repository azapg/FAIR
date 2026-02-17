import { useQueryClient } from "@tanstack/react-query";
import { ReactNode, useEffect, useRef } from "react";
import { useSessionStore } from "@/store/session-store";
import { submissionsKeys } from "@/hooks/use-submissions";
import { getWebSocketUrl } from "@/lib/api";

export function SessionSocketProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const {
    socket,
    activeAssignmentId,
    sessionsByAssignment,
    setSocket,
    setCurrentSession,
    addLog,
    clearLogs,
  } = useSessionStore();
  const currentSession = activeAssignmentId
    ? sessionsByAssignment[activeAssignmentId] ?? null
    : null;
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
    if (!activeAssignmentId) return;
    clearLogs(activeAssignmentId);

    const wsUrl = getWebSocketUrl(`/api/sessions/${currentSession.id}`);
    const newSocket = new WebSocket(wsUrl);
    setSocket(newSocket);

    newSocket.onopen = () => {
      lastSessionId.current = currentSession.id;
      if (activeAssignmentId) {
        clearLogs(activeAssignmentId);
      }
    };

    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      try {
        if (activeAssignmentId) {
          addLog(activeAssignmentId, data);
        }
      } catch (e) {
        // noop
      }

      if (data.type == "close") {
        newSocket.close();
        setSocket(null);
        if (activeAssignmentId) {
          setCurrentSession(activeAssignmentId, null);
        }
        return;
      }

      if (data.type == "update") {
        switch (data?.payload?.object) {
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
  }, [activeAssignmentId, currentSession?.id]);

  return <>{children}</>;
}

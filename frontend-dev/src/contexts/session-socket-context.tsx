import {useQueryClient} from "@tanstack/react-query";
import {ReactNode, useEffect, useRef} from "react";
import {useSessionStore} from "@/store/session-store";

export function SessionSocketProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const {socket, currentSession, setSocket, setCurrentSession} = useSessionStore();
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

    const wsUrl = `ws://localhost:8000/api/sessions/${currentSession.id}`;
    const newSocket = new WebSocket(wsUrl);
    setSocket(newSocket);

    newSocket.onopen = () => {
      lastSessionId.current = currentSession.id;
    }

    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data);

      if (data.type == "close") {
        newSocket.close();
        setSocket(null);
        setCurrentSession(null);
        return;
      }

    }

    newSocket.onclose = () => {
      setSocket(null);
    }

    newSocket.onerror = () => {
      newSocket.close();
    }

    return () => {
      if (newSocket.readyState === WebSocket.OPEN) {
        newSocket.close();
      }
    }

  }, [currentSession?.id]);

  return <>{children}</>;
}
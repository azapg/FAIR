import { create } from 'zustand';
import { persist } from "zustand/middleware";
import {Submission} from "@/hooks/use-submissions";
import { AuthUser } from "@/contexts/auth-context";

type Session = {
  id: string;
  runner: AuthUser; // user object
  status: 'pending' | 'running' | 'success' | 'failure' | 'cancelled';
  started_at: string;
  finished_at: string | null;
  logs: SessionLog[];
  submissions: Submission[];
}

export type SessionLog = {
  index: number;
  ts: string;
  type: string;
  level: 'debug' | 'info' | 'warning' | 'error' | string;
  payload?: {
    message?: string;
    reason?: string;
    plugin?: {
      id?: string;
      name?: string;
      hash?: string;
      author?: string;
      version?: string;
      source?: string;
      type?: string;
    };
    description?: string;
    image?: {
      src?: string;
      alt?: string;
      mime_type?: string;
    };
    images?: Array<{
      src?: string;
      alt?: string;
      mime_type?: string;
    }>;
    [key: string]: any;
  };
}

type State = {
  socket: WebSocket | null;
  currentSession: Session | null;
  sessionLogs: SessionLog[];
  lastLogIndex: number;
}

type Actions = {
  setSocket: (socket: State['socket']) => void;
  setCurrentSession: (session: State['currentSession']) => void;
  setLogs: (logs: SessionLog[]) => void;
  addLog: (log: SessionLog) => void;
  clearLogs: () => void;
}

export const useSessionStore = create<State & Actions>()(
  persist(
    (set) => ({
      socket: null,
      currentSession: null,
      sessionLogs: [],
      lastLogIndex: -1,
      setSocket: (socket) => set({ socket }),
      setCurrentSession: (session) => set({ currentSession: session }),
      setLogs: (logs) => set({ sessionLogs: logs, lastLogIndex: logs.reduce((max, l) => Math.max(max, l.index ?? -1), -1) }),
      addLog: (log) => set((state) => {
        if (typeof log.index === 'number' && log.index <= state.lastLogIndex) {
          // Ignore duplicates/out-of-order old entries
          return state;
        }
        return {
          sessionLogs: [...state.sessionLogs, log],
          lastLogIndex: typeof log.index === 'number' ? log.index : state.lastLogIndex,
        };
      }),
      clearLogs: () => set({ sessionLogs: [], lastLogIndex: -1 }),
    }),
    {
      name: 'fair-session'
    }
  )
);

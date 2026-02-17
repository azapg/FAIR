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
    file?: {
      name?: string;
      content?: string;
      file_type?: "text" | "markdown" | string;
      mime_type?: "text/plain" | "text/markdown" | string;
      encoding?: string;
      size_bytes?: number;
      language?: string;
    };
    [key: string]: any;
  };
}

type State = {
  socket: WebSocket | null;
  activeAssignmentId: string | null;
  sessionsByAssignment: Record<string, Session | null>;
  logsByAssignment: Record<string, SessionLog[]>;
  lastLogIndexByAssignment: Record<string, number>;
}

type Actions = {
  setSocket: (socket: State['socket']) => void;
  setCurrentSession: (assignmentId: string, session: Session | null) => void;
  setLogs: (assignmentId: string, logs: SessionLog[]) => void;
  addLog: (assignmentId: string, log: SessionLog) => void;
  clearLogs: (assignmentId: string) => void;
}

export const useSessionStore = create<State & Actions>()(
  persist(
    (set) => ({
      socket: null,
      activeAssignmentId: null,
      sessionsByAssignment: {},
      logsByAssignment: {},
      lastLogIndexByAssignment: {},
      setSocket: (socket) => set({ socket }),
      setCurrentSession: (assignmentId, session) =>
        set((state) => ({
          activeAssignmentId: session
            ? assignmentId
            : state.activeAssignmentId === assignmentId
              ? null
              : state.activeAssignmentId,
          sessionsByAssignment: {
            ...state.sessionsByAssignment,
            [assignmentId]: session,
          },
        })),
      setLogs: (assignmentId, logs) =>
        set((state) => ({
          logsByAssignment: { ...state.logsByAssignment, [assignmentId]: logs },
          lastLogIndexByAssignment: {
            ...state.lastLogIndexByAssignment,
            [assignmentId]: logs.reduce((max, l) => Math.max(max, l.index ?? -1), -1),
          },
        })),
      addLog: (assignmentId, log) => set((state) => {
        const lastLogIndex = state.lastLogIndexByAssignment[assignmentId] ?? -1;
        if (typeof log.index === 'number' && log.index <= lastLogIndex) {
          // Ignore duplicates/out-of-order old entries
          return state;
        }
        return {
          logsByAssignment: {
            ...state.logsByAssignment,
            [assignmentId]: [...(state.logsByAssignment[assignmentId] ?? []), log],
          },
          lastLogIndexByAssignment: {
            ...state.lastLogIndexByAssignment,
            [assignmentId]: typeof log.index === 'number' ? log.index : lastLogIndex,
          },
        };
      }),
      clearLogs: (assignmentId) => set((state) => ({
        logsByAssignment: {
          ...state.logsByAssignment,
          [assignmentId]: [],
        },
        lastLogIndexByAssignment: {
          ...state.lastLogIndexByAssignment,
          [assignmentId]: -1,
        },
      })),
    }),
    {
      name: 'fair-session'
    }
  )
);

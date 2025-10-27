import { create } from 'zustand';
import { persist } from "zustand/middleware";
import {SubmissionStatus} from "@/app/assignment/components/submissions/submissions";


// TODO: Submission type isn't even finished, it is missing feedback, grade, etc.
// TODO: Also, I should update the backend to not send snake case 🤮🤮🤮
type Submission = {
  id: string;
  assignment_id: string;
  submitter_id: string;
  submitted_at: string;
  status: SubmissionStatus;
  official_run_id: string | null;
  artifacts: any[];
}

type Session = {
  id: string;
  run_by: string; // user id
  status: 'pending' | 'running' | 'success' | 'failure' | 'cancelled';
  started_at: string;
  finished_at: string | null;
  logs: any[];
  submissions: Submission[];
}

export type SessionLog = {
  index: number;
  type: string;
  ts?: string | null;
  level?: 'debug' | 'info' | 'warning' | 'error' | string;
  plugin?: string | null;
  message?: string | null;
  object?: string | null;
  payload?: any;
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
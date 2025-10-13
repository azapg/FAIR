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

type State = {
  socket: WebSocket | null;
  currentSession: Session | null;
}

type Actions = {
  setSocket: (socket: State['socket']) => void;
  setCurrentSession: (session: State['currentSession']) => void;
}

export const useSessionStore = create<State & Actions>()(
  persist(
    (set) => ({
      socket: null,
      currentSession: null,
      setSocket: (socket) => set({ socket }),
      setCurrentSession: (session) => set({ currentSession: session }),
    }),
    {
      name: 'fair-session'
    }
  )
);
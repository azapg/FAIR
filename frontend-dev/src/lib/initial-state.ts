import type { AuthUser } from "@/contexts/auth-context";

export interface FairInitialState {
  auth: {
    isAuthenticated: boolean;
    user: AuthUser | null;
  };
  features: {
    emailEnabled: boolean;
    enforceEmailVerification: boolean;
  };
  platform: {
    deploymentMode: "COMMUNITY" | "ENTERPRISE";
    baseUrl: string;
  };
  injectedAt: string;
}

const SCRIPT_ID = "__FAIR_INITIAL_STATE__";

export function getInitialState(): FairInitialState {
  if (typeof document === "undefined") {
    throw new Error("Initial state is only available in browser context.");
  }

  const script = document.getElementById(SCRIPT_ID);
  if (!script || script.textContent === null) {
    throw new Error("Initial state not found in document.");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(script.textContent);
  } catch {
    throw new Error("Initial state JSON is invalid.");
  }

  if (!parsed || typeof parsed !== "object") {
    throw new Error("Initial state has invalid shape.");
  }

  return parsed as FairInitialState;
}

export function getOptionalInitialState(): FairInitialState | null {
  try {
    return getInitialState();
  } catch {
    return null;
  }
}

import { useEffect } from "react";
import { act, render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiGet, apiPost } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ default: { get: apiGet, post: apiPost } }));

import { AuthProvider, useAuth } from "./auth-context";

type AuthValue = ReturnType<typeof useAuth>;

function Probe({ onValue }: { onValue: (value: AuthValue) => void }) {
  const value = useAuth();
  useEffect(() => onValue(value), [onValue, value]);
  return null;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    localStorage.clear();
  });

  it("hydrates browser authentication from the HttpOnly cookie", async () => {
    apiGet.mockResolvedValueOnce({
      data: {
        id: "user-1",
        name: "Cookie User",
        email: "cookie@example.test",
        role: "user",
        capabilities: ["join_course"],
        settings: {},
        isVerified: true,
      },
    });
    let current!: AuthValue;

    render(
      <AuthProvider>
        <Probe onValue={(value) => { current = value; }} />
      </AuthProvider>,
    );

    await waitFor(() => expect(current.isAuthenticated).toBe(true));
    expect(current.user?.email).toBe("cookie@example.test");
    expect(apiGet).toHaveBeenCalledWith("/auth/me");
    expect(localStorage.getItem("token")).toBeNull();
  });

  it("clears the cookie and keeps UI state unauthenticated when profile loading fails", async () => {
    apiGet.mockRejectedValueOnce(new Error("No initial session"));
    apiPost.mockResolvedValueOnce({ data: { access_token: "not-used-by-browser" } });
    apiGet.mockRejectedValueOnce(new Error("Profile unavailable"));
    apiPost.mockResolvedValueOnce({ data: { detail: "Logged out" } });
    let current!: AuthValue;

    render(
      <AuthProvider>
        <Probe onValue={(value) => { current = value; }} />
      </AuthProvider>,
    );
    await waitFor(() => expect(current.loading).toBe(false));

    await act(async () => {
      await expect(current.login({ username: "user@example.test", password: "secret" }))
        .rejects.toThrow("Profile unavailable");
    });

    expect(current.isAuthenticated).toBe(false);
    expect(current.user).toBeNull();
    expect(apiPost).toHaveBeenLastCalledWith("/auth/logout");
    expect(localStorage.getItem("token")).toBeNull();
  });
});

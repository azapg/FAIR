import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiGet, apiPatch } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ default: { get: apiGet, patch: apiPatch } }));
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

import { useUpdateUserSetting, userSettingsKeys } from "./use-user-settings";

describe("useUpdateUserSetting", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPatch.mockReset();
  });

  it("serializes rapid writes and derives the second from the first result", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(userSettingsKeys.me(), {
      preferences: { theme: "light", language: "en" },
    });
    let resolveFirst!: (value: unknown) => void;
    const firstResponse = new Promise((resolve) => { resolveFirst = resolve; });
    apiPatch
      .mockImplementationOnce(() => firstResponse)
      .mockImplementationOnce((_url, body) => Promise.resolve({ data: { settings: body.settings } }));

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => ({
      first: useUpdateUserSetting(),
      second: useUpdateUserSetting(),
    }), { wrapper });

    let firstWrite!: Promise<unknown>;
    let secondWrite!: Promise<unknown>;
    act(() => {
      firstWrite = result.current.first.mutateAsync({ path: "preferences.theme", value: "dark" });
      secondWrite = result.current.second.mutateAsync({ path: "preferences.language", value: "es" });
    });

    await waitFor(() => expect(apiPatch).toHaveBeenCalledTimes(1));
    resolveFirst({
      data: { settings: { preferences: { theme: "dark", language: "en" } } },
    });
    await waitFor(() => expect(apiPatch).toHaveBeenCalledTimes(2));
    expect(apiPatch.mock.calls[1][1].settings).toEqual({
      preferences: { theme: "dark", language: "es" },
    });

    await Promise.all([firstWrite, secondWrite]);
  });
});

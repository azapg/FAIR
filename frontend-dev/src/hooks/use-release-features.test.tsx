import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useReleaseFeatures } from "./use-release-features";

const state = vi.hoisted(() => ({ data: undefined as any, isPending: false }));
vi.mock("@/hooks/use-system-config", () => ({ useSystemConfig: () => state }));
afterEach(() => {
  state.data = undefined;
  state.isPending = false;
});
const features = {
  todo: true,
  inbox: true,
  extensions: true,
  course_content: true,
  gradebook: true,
};
describe("release configuration", () => {
  it.each(["stable", "canary", undefined])(
    "never opts %s into experiments",
    (release_channel) => {
      state.data = { release_channel, features };
      const { result } = renderHook(useReleaseFeatures);
      expect(result.current.todo).toBe(false);
      expect(result.current.extensions).toBe(false);
      expect(result.current.dashboard).toBe(false);
    },
  );
  it("keeps experiments hidden while loading and after config failure", () => {
    state.isPending = true;
    const { result, rerender } = renderHook(useReleaseFeatures);
    expect(result.current.inbox).toBe(false);
    state.isPending = false;
    rerender();
    expect(result.current.course_content).toBe(false);
  });
  it("honors individual Nightly flags and dashboard prerequisites", () => {
    state.data = {
      release_channel: "nightly",
      features: { ...features, gradebook: false },
    };
    const { result } = renderHook(useReleaseFeatures);
    expect(result.current.todo).toBe(true);
    expect(result.current.inbox).toBe(true);
    expect(result.current.course_content).toBe(true);
    expect(result.current.gradebook).toBe(false);
    expect(result.current.dashboard).toBe(false);
  });
});

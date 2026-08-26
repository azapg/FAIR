import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useSidebarSwipe } from "./use-sidebar-swipe";

function touch(type: string, x: number, y: number, cancelable = true) {
  const event = new Event(type, { bubbles: true, cancelable }) as Event & {
    touches: Array<{ clientX: number; clientY: number }>;
  };
  Object.defineProperty(event, "touches", {
    value: [{ clientX: x, clientY: y }],
  });
  return event;
}

function swipe(points: Array<[number, number]>, cancelable = true) {
  const [startX, startY] = points[0];
  window.dispatchEvent(touch("touchstart", startX, startY));
  for (const [x, y] of points.slice(1)) {
    window.dispatchEvent(touch("touchmove", x, y, cancelable));
  }
  window.dispatchEvent(touch("touchend", startX, startY));
}

describe("useSidebarSwipe", () => {
  it("opens the left sidebar on rightward edge swipe", () => {
    const onOpenChange = vi.fn();
    renderHook(() =>
      useSidebarSwipe({
        side: "left",
        open: false,
        onOpenChange,
        enabled: true,
      }),
    );

    swipe([
      [10, 300],
      [100, 305],
    ]);

    expect(onOpenChange).toHaveBeenCalledWith(true);
  });

  it("closes the left sidebar on leftward swipe", () => {
    const onOpenChange = vi.fn();
    renderHook(() =>
      useSidebarSwipe({ side: "left", open: true, onOpenChange, enabled: true }),
    );

    swipe([
      [200, 300],
      [100, 305],
    ]);

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("ignores vertical scrolls", () => {
    const onOpenChange = vi.fn();
    renderHook(() =>
      useSidebarSwipe({
        side: "left",
        open: false,
        onOpenChange,
        enabled: true,
      }),
    );

    swipe([
      [10, 100],
      [20, 400],
    ]);

    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it("opens the left sidebar on rightward swipe from anywhere when closed", () => {
    const onOpenChange = vi.fn();
    renderHook(() =>
      useSidebarSwipe({
        side: "left",
        open: false,
        onOpenChange,
        enabled: true,
      }),
    );

    swipe([
      [200, 300],
      [320, 305],
    ]);

    expect(onOpenChange).toHaveBeenCalledWith(true);
  });
});

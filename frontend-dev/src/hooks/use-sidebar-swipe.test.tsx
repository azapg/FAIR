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

function swipe(
  points: Array<[number, number]>,
  cancelable = true,
  target: EventTarget = window,
) {
  const [startX, startY] = points[0];
  target.dispatchEvent(touch("touchstart", startX, startY));
  const moves: Event[] = [];
  for (const [x, y] of points.slice(1)) {
    const event = touch("touchmove", x, y, cancelable);
    target.dispatchEvent(event);
    moves.push(event);
  }
  target.dispatchEvent(touch("touchend", startX, startY));
  return moves;
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

  it("yields to explicitly protected nested gestures", () => {
    const onOpenChange = vi.fn();
    const gestureRegion = document.createElement("div");
    gestureRegion.dataset.sidebarSwipe = "ignore";
    document.body.appendChild(gestureRegion);
    renderHook(() =>
      useSidebarSwipe({
        side: "left",
        open: false,
        onOpenChange,
        enabled: true,
      }),
    );

    const moves = swipe(
      [
        [10, 300],
        [100, 305],
      ],
      true,
      gestureRegion,
    );

    expect(onOpenChange).not.toHaveBeenCalled();
    expect(moves[0].defaultPrevented).toBe(false);
    gestureRegion.remove();
  });

  it("yields to horizontally scrollable regions", () => {
    const onOpenChange = vi.fn();
    const scrollRegion = document.createElement("div");
    scrollRegion.style.overflowX = "auto";
    Object.defineProperties(scrollRegion, {
      clientWidth: { value: 200 },
      scrollWidth: { value: 500 },
    });
    document.body.appendChild(scrollRegion);
    renderHook(() =>
      useSidebarSwipe({
        side: "left",
        open: false,
        onOpenChange,
        enabled: true,
      }),
    );

    const moves = swipe(
      [
        [200, 300],
        [320, 305],
      ],
      true,
      scrollRegion,
    );

    expect(onOpenChange).not.toHaveBeenCalled();
    expect(moves[0].defaultPrevented).toBe(false);
    scrollRegion.remove();
  });
});

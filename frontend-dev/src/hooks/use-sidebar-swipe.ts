import * as React from "react";

const SWIPE_THRESHOLD_PX = 50;
const DIRECTIONAL_RATIO = 1.2;
const SCROLL_LOCK_PX = 10;

export function useSidebarSwipe({
  side,
  open,
  onOpenChange,
  enabled,
}: {
  side: "left" | "right";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  enabled: boolean;
}) {
  const startRef = React.useRef<{ x: number; y: number } | null>(null);
  const lockedRef = React.useRef(false);

  React.useEffect(() => {
    if (!enabled) return;

    const isHorizontalSwipe = (dx: number, dy: number) =>
      Math.abs(dx) >= SWIPE_THRESHOLD_PX &&
      Math.abs(dx) > Math.abs(dy) * DIRECTIONAL_RATIO;

    const opensFromEdge = (dx: number) => {
      if (open || dx === 0) return false;
      // If any sidebar is currently open, don't open another - close has priority
      if (document.querySelector('[data-slot="sheet-overlay"]')) return false;
      return side === "left" ? dx > 0 : dx < 0;
    };

    const closesWithSwipe = (dx: number) => {
      if (!open) return false;
      return side === "left" ? dx < 0 : dx > 0;
    };

    const handleTouchStart = (event: TouchEvent) => {
      if (event.touches.length !== 1) return;
      const touch = event.touches[0];
      startRef.current = { x: touch.clientX, y: touch.clientY };
      lockedRef.current = false;
    };

    const handleTouchMove = (event: TouchEvent) => {
      const start = startRef.current;
      if (!start) return;
      const touch = event.touches[0];
      if (!touch) return;

      const dx = touch.clientX - start.x;
      const dy = touch.clientY - start.y;

      if (
        !lockedRef.current &&
        Math.abs(dx) > SCROLL_LOCK_PX &&
        Math.abs(dx) > Math.abs(dy)
      ) {
        lockedRef.current = true;
      }

      if (lockedRef.current && event.cancelable) {
        event.preventDefault();
      }

      if (isHorizontalSwipe(dx, dy)) {
        if (opensFromEdge(dx) || closesWithSwipe(dx)) {
          onOpenChange(!open);
          startRef.current = null;
          lockedRef.current = false;
        }
      }
    };

    const handleTouchEnd = () => {
      startRef.current = null;
      lockedRef.current = false;
    };

    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", handleTouchEnd);
    window.addEventListener("touchcancel", handleTouchEnd);

    return () => {
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
      window.removeEventListener("touchcancel", handleTouchEnd);
    };
  }, [side, open, onOpenChange, enabled]);
}

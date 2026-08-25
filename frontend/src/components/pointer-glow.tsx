"use client";

import { useEffect, useRef } from "react";

/**
 * Backdrop reactivity: a soft light that trails the cursor, and a matching
 * parallax nudge on the cloud layer so the sky has depth behind the content.
 *
 * Everything is written to CSS custom properties on <html> from inside one
 * requestAnimationFrame loop — never React state. A pointermove listener that
 * setState'd would re-render the whole console on every mouse event; this
 * touches two custom properties and lets the compositor do the rest.
 *
 * The position eases toward the pointer rather than snapping to it (a simple
 * lerp per frame), which is what makes it read as light drifting rather than
 * a cursor decoration.
 */
export function PointerGlow() {
  const frame = useRef(0);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reduced.matches) return;

    const root = document.documentElement;
    const target = { x: window.innerWidth / 2, y: window.innerHeight * 0.3 };
    const eased = { ...target };
    let glow = 0;
    let glowTarget = 0;
    let idle: ReturnType<typeof setTimeout> | undefined;

    function onMove(e: PointerEvent) {
      target.x = e.clientX;
      target.y = e.clientY;
      glowTarget = 0.55;
      clearTimeout(idle);
      // Fade back out once the pointer settles, so a parked cursor doesn't
      // leave a permanent hotspot on the page.
      idle = setTimeout(() => {
        glowTarget = 0.16;
      }, 1400);
    }

    function onLeave() {
      glowTarget = 0;
    }

    function tick() {
      eased.x += (target.x - eased.x) * 0.07;
      eased.y += (target.y - eased.y) * 0.07;
      glow += (glowTarget - glow) * 0.05;

      root.style.setProperty("--pointer-x", `${eased.x}px`);
      root.style.setProperty("--pointer-y", `${eased.y}px`);
      root.style.setProperty("--pointer-glow", glow.toFixed(3));

      // Clouds drift against the pointer, a few px — enough to feel like
      // depth, not enough to notice as movement.
      const px = (eased.x / window.innerWidth - 0.5) * -18;
      const py = (eased.y / window.innerHeight - 0.5) * -10;
      root.style.setProperty("--parallax-x", `${px.toFixed(2)}px`);
      root.style.setProperty("--parallax-y", `${py.toFixed(2)}px`);

      frame.current = requestAnimationFrame(tick);
    }

    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    frame.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frame.current);
      clearTimeout(idle);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return <div className="console-glow" aria-hidden="true" />;
}

"use client";

import { useEffect, useRef } from "react";

/**
 * Backdrop reactivity: a soft light that trails the cursor, and a matching
 * parallax nudge on the cloud layer so the sky has depth behind the content.
 *
 * Everything is written to CSS custom properties on <html> from inside one
 * requestAnimationFrame loop — never React state. A pointermove listener that
 * setState'd would re-render the whole console on every mouse event; this
 * touches a few custom properties and lets the compositor do the rest.
 *
 * The position eases toward the pointer rather than snapping to it (a simple
 * lerp per frame), which is what makes it read as light drifting rather than
 * a cursor decoration.
 *
 * THE LOOP SLEEPS. It used to call rAF unconditionally, forever, so a parked
 * cursor still cost a frame of work every 16ms for as long as the tab was
 * open — and because these properties live on the document element, each of
 * those frames invalidated inherited style across the entire tree. That is
 * cheap on an empty page and not cheap at all on the workspace, where it was
 * competing with a live preview iframe and an open SSE stream. So the loop
 * now runs only while something is still moving, and the last frame before
 * it stops snaps the eased values onto their targets so nothing is left
 * visibly mid-transit.
 */
export function PointerGlow() {
  const frame = useRef(0);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    // A coarse pointer has no cursor to trail, so the whole effect is dead
    // weight on a touch device — and it is the expensive kind of dead weight.
    const fine = window.matchMedia("(pointer: fine)");
    if (reduced.matches || !fine.matches) return;

    const root = document.documentElement;
    const target = { x: window.innerWidth / 2, y: window.innerHeight * 0.3 };
    const eased = { ...target };
    let glow = 0;
    let glowTarget = 0;
    let idle: ReturnType<typeof setTimeout> | undefined;
    let running = false;

    // Below this, the remaining movement is sub-pixel and nobody can see it,
    // so it is a better place to stop than to keep easing toward zero.
    const EPSILON = 0.35;

    function paint() {
      root.style.setProperty("--pointer-x", `${eased.x.toFixed(1)}px`);
      root.style.setProperty("--pointer-y", `${eased.y.toFixed(1)}px`);
      root.style.setProperty("--pointer-glow", glow.toFixed(3));
      // Clouds drift against the pointer, a few px — enough to feel like
      // depth, not enough to notice as movement.
      const px = (eased.x / window.innerWidth - 0.5) * -18;
      const py = (eased.y / window.innerHeight - 0.5) * -10;
      root.style.setProperty("--parallax-x", `${px.toFixed(2)}px`);
      root.style.setProperty("--parallax-y", `${py.toFixed(2)}px`);
    }

    function tick() {
      eased.x += (target.x - eased.x) * 0.07;
      eased.y += (target.y - eased.y) * 0.07;
      glow += (glowTarget - glow) * 0.05;

      const settled =
        Math.abs(target.x - eased.x) < EPSILON &&
        Math.abs(target.y - eased.y) < EPSILON &&
        Math.abs(glowTarget - glow) < 0.004;

      if (settled) {
        // Land exactly on the target rather than near it, so the next wake
        // does not start from a stale offset.
        eased.x = target.x;
        eased.y = target.y;
        glow = glowTarget;
        paint();
        running = false;
        return;
      }

      paint();
      frame.current = requestAnimationFrame(tick);
    }

    function wake() {
      if (running) return;
      running = true;
      frame.current = requestAnimationFrame(tick);
    }

    function onMove(e: PointerEvent) {
      target.x = e.clientX;
      target.y = e.clientY;
      glowTarget = 0.55;
      clearTimeout(idle);
      // Fade back out once the pointer settles, so a parked cursor doesn't
      // leave a permanent hotspot on the page.
      idle = setTimeout(() => {
        glowTarget = 0.16;
        wake();
      }, 1400);
      wake();
    }

    function onLeave() {
      glowTarget = 0;
      wake();
    }

    // Nothing to ease toward while the tab is in the background, and a
    // backgrounded rAF that does wake up is pure waste.
    function onVisibility() {
      if (document.hidden) {
        cancelAnimationFrame(frame.current);
        running = false;
      }
    }

    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    document.addEventListener("visibilitychange", onVisibility);
    paint();

    return () => {
      cancelAnimationFrame(frame.current);
      clearTimeout(idle);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return <div className="console-glow" aria-hidden="true" />;
}

import { CloudField } from "@/components/cloud-field";
import { PointerGlow } from "@/components/pointer-glow";

/**
 * The sky, the stars and the cursor light — the home screen's atmosphere.
 *
 * Deliberately NOT in the root layout. It used to be, which meant the
 * workspace carried a full-viewport fractal-noise filter, two animated star
 * layers and a per-frame rAF loop for the entire length of a run — at the one
 * moment the tab is busiest, streaming SSE and hydrating a live preview of
 * the built site in an iframe. The backdrop is decoration for an empty prompt
 * box; the workspace has a page being built to look at instead.
 */
export function ConsoleBackdrop() {
  return (
    <>
      <CloudField />
      <PointerGlow />
      <div className="console-stars" aria-hidden="true" />
    </>
  );
}

"use client";

import dynamic from "next/dynamic";

/**
 * The workspace's heavy panels, each in its own chunk.
 *
 * Any one project shows at most two of them — the studio and the preview, or
 * the feed and the build canvas, or a gate — but imported directly all four
 * were in the page's first download and mounted in a single React commit,
 * which a transition cannot slice: measured as one 160 ms block on
 * Lighthouse's mobile CPU, holding /build at 97. Split, each downloads only
 * when its project needs it and mounts in its own smaller commit.
 *
 * Every placeholder fills the box it stands in for (`h-full` inside a fixed
 * column or panel), so a panel arriving never moves anything else.
 */

function Placeholder({ label }: { label?: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      {label ? label : <span className="size-6 animate-pulse rounded-md bg-muted" />}
    </div>
  );
}

function ChatPlaceholder() {
  return (
    <div className="flex h-full flex-col gap-3 px-4 py-4">
      <div className="h-6 w-1/3 animate-pulse rounded bg-muted" />
      <div className="grid grid-cols-2 gap-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-muted/70" />
        ))}
      </div>
    </div>
  );
}

export const StudioPanel = dynamic(
  () => import("@/components/studio-panel").then((m) => m.StudioPanel),
  { ssr: false, loading: () => <ChatPlaceholder /> }
);

export const PreviewPane = dynamic(
  () => import("@/components/preview-pane").then((m) => m.PreviewPane),
  { ssr: false, loading: () => <Placeholder /> }
);

export const BuildCanvas = dynamic(
  () => import("@/components/build-canvas").then((m) => m.BuildCanvas),
  { ssr: false, loading: () => <Placeholder /> }
);

// Not `h-full`: in the chat column a gate is one card in a scrolling list,
// below the run's progress. A short block holds its place until it arrives.
export const GatePanel = dynamic(() => import("@/components/gate-panel").then((m) => m.GatePanel), {
  ssr: false,
  loading: () => <div className="h-24 animate-pulse rounded-xl bg-muted/60" />,
});

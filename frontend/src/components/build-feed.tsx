"use client";

import { useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { AlertTriangle, Check, CircleDashed, Loader2, Play } from "lucide-react";

import { cn } from "@/lib/utils";
import type { AssetPlanEntry, BlackboardAsset, Direction, GateAnswer, GateInfo, RunEvent } from "@/lib/api";
import { AssetTray } from "@/components/asset-tray";
import { SparrowMark } from "@/components/sparrow-mark";
import { SourceCard } from "@/components/source-card";
import { GatePanel } from "@/components/gate-panel";
import { Button } from "@/components/ui/button";

// Matches backend/src/sparrow/orchestrator.py's Stage enum, in order —
// needed to infer "done" for stages that end via a gate Halt rather than
// their own kind="done" event (design and verify never emit one; they stop
// at gate:design / gate:preview instead).
const FULL_ORDER = [
  "brief", "gate:brief", "sources", "design", "gate:design", "compose",
  "content", "gate:assets", "assets", "build", "verify", "gate:preview", "done",
];

const DISPLAY_STAGES: { key: string; label: string }[] = [
  { key: "brief", label: "Brief" },
  { key: "sources", label: "Sources" },
  { key: "design", label: "Design" },
  { key: "compose", label: "Layout" },
  { key: "content", label: "Content" },
  { key: "assets", label: "Assets" },
  { key: "build", label: "Build" },
  { key: "verify", label: "Verify" },
];

type StageStatus = "pending" | "active" | "done" | "failed";

/**
 * Status for every displayed stage, in one pass over the events.
 *
 * This used to be a per-stage function that filtered and scanned the whole
 * event array, called twice per row (once for the icon, once for the text
 * colour) — sixteen full scans of a list that grows all run, on every one of
 * the hundreds of SSE events that arrive. Same answers, one pass, and the
 * result is memoised so a re-render that did not add an event is free.
 */
function stageStatuses(
  events: RunEvent[],
  stoppedStage?: string | null
): Record<string, StageStatus> {
  // How far the run has got overall: the furthest-ordered stage seen. Any
  // display stage before it has necessarily finished, which is what covers
  // design and verify — they end at a gate and never emit their own "done".
  let furthest = -1;
  const own = new Map<string, { any: boolean; done: boolean; failed: boolean }>();

  for (const e of events) {
    const at = FULL_ORDER.indexOf(e.stage);
    if (at > furthest) furthest = at;
    const rec = own.get(e.stage) ?? { any: false, done: false, failed: false };
    rec.any = true;
    if (e.kind === "done") rec.done = true;
    if (e.kind === "failed") rec.failed = true;
    own.set(e.stage, rec);
  }

  // A resumed project has no event stream behind it — the only record of how
  // far it got is the stage the API reports, so anything ordered before that
  // stage has already run.
  const stoppedAt = stoppedStage ? FULL_ORDER.indexOf(stoppedStage) : -1;

  const out: Record<string, StageStatus> = {};
  for (const { key } of DISPLAY_STAGES) {
    const idx = FULL_ORDER.indexOf(key);
    const rec = own.get(key);
    if (rec?.failed) out[key] = "failed";
    else if (furthest > idx) out[key] = "done";
    else if (rec?.done) out[key] = "done";
    else if (rec?.any) out[key] = "active";
    else if (stoppedAt > -1 && idx < stoppedAt) out[key] = "done";
    else out[key] = "pending";
  }
  return out;
}

const STATUS_ICON: Record<StageStatus, React.ReactNode> = {
  pending: <CircleDashed className="size-3.5 text-muted-foreground" />,
  active: <Loader2 className="size-3.5 animate-spin text-foreground" />,
  done: <Check className="size-3.5 text-emerald-400" />,
  failed: <AlertTriangle className="size-3.5 text-destructive" />,
};

function domainOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export function BuildFeed({
  prompt,
  urls,
  phase,
  events,
  spent,
  gate,
  directions,
  errorMessage,
  showGateInline,
  projectId,
  stoppedStage,
  gateError,
  assetPlan = [],
  madeAssets = [],
  previewReady = false,
  onResume,
  onAnswerGate,
}: {
  prompt: string;
  urls: string[];
  phase:
    | "loading"
    | "interview"
    | "create"
    | "run"
    | "gate"
    | "paused"
    | "done"
    | "error";
  events: RunEvent[];
  spent: number;
  gate: GateInfo | null;
  directions: Direction[] | null;
  errorMessage: string | null;
  showGateInline: boolean;
  projectId: string;
  stoppedStage: string | null;
  gateError?: string | null;
  assetPlan?: AssetPlanEntry[];
  madeAssets?: BlackboardAsset[];
  previewReady?: boolean;
  onResume: () => void;
  onAnswerGate: (payload: GateAnswer) => void;
}) {
  const logRef = useRef<HTMLDivElement>(null);
  const statuses = useMemo(
    () => stageStatuses(events, stoppedStage),
    [events, stoppedStage]
  );

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [events]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <SparrowMark className="size-4" />
          <span className="text-sm font-medium text-foreground">sparrow</span>
        </div>
        {spent > 0 && (
          <span className="text-xs text-muted-foreground">${spent.toFixed(4)} spent</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mb-2 rounded-xl bg-secondary/60 px-3.5 py-2.5 text-sm text-foreground">
          {prompt}
        </div>

        {urls.length > 0 && (
          <div className="mb-4">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Reference sites</p>
            <div className="flex flex-col gap-1.5">
              {urls.map((u) => (
                <SourceCard
                  key={u}
                  source={{
                    id: u,
                    title: domainOf(u),
                    domain: domainOf(u),
                    url: u,
                    description: "Used to rank structure and section order",
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {(phase === "loading" || phase === "interview" || phase === "create") && (
          <div className="mb-4 flex items-center gap-2.5 text-sm text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            {phase === "interview"
              ? "Drafting the brief…"
              : phase === "create"
                ? "Creating the project…"
                : "Loading…"}
          </div>
        )}

        {phase !== "loading" && phase !== "interview" && phase !== "create" && (
          <>
            <p className="mb-3 text-xs font-medium text-muted-foreground">Building your site</p>
            <ul className="mb-4 flex flex-col gap-2.5">
              {DISPLAY_STAGES.map(({ key, label }) => (
                <li key={key} className="flex items-center gap-2.5 text-sm">
                  {STATUS_ICON[statuses[key]]}
                  <span
                    className={cn(
                      statuses[key] === "pending"
                        ? "text-muted-foreground"
                        : "text-foreground"
                    )}
                  >
                    {label}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        {events.length > 0 && (
          <div
            ref={logRef}
            className="mb-4 max-h-48 overflow-y-auto rounded-lg border border-border bg-black/20 p-2.5 font-mono text-[11px] leading-relaxed text-muted-foreground"
          >
            {events.map((e, i) => (
              <div key={i} className="truncate">
                <span className="text-foreground/70">{e.stage}</span> · {e.message}
                {e.cost > 0 && <span className="text-muted-foreground"> · ${e.cost.toFixed(4)}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Once the preview has the main pane the canvas (and its tray) is
            gone, so the record of what was made moves here — small, next to
            the site it went into. Not shown while the canvas is up: the same
            list twice, one of them cramped, helps nobody. */}
        {previewReady && assetPlan.length > 0 && (
          <div className="mb-4">
            <AssetTray
              plan={assetPlan}
              made={madeAssets}
              events={events}
              projectId={projectId}
              compact
            />
          </div>
        )}

        {/* Only when the preview pane isn't already showing it — see
            build-workspace.tsx, which gives the design gate the main pane
            while there is nothing built to preview. */}
        {phase === "gate" && gate?.awaiting && showGateInline && (
          <GatePanel
            gate={gate}
            directions={directions}
            layout="compact"
            projectId={projectId}
            serverError={gateError}
            onAnswerGate={onAnswerGate}
          />
        )}

        {/* Stopped part-way and not waiting on anyone. Resuming costs real
            model calls, so it is offered as a button and never taken
            automatically on open. */}
        {phase === "paused" && (
          <div className="rounded-xl border border-border bg-secondary/40 p-3.5">
            <p className="text-sm text-foreground">
              Stopped at {(stoppedStage ?? "an earlier stage").replace(/^gate:/, "")}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Nothing is running. Continuing runs the next stage and spends on
              model calls{spent > 0 ? ` — $${spent.toFixed(4)} so far` : ""}.
            </p>
            <Button type="button" size="sm" className="mt-3" onClick={onResume}>
              <Play className="size-3" /> Resume the run
            </Button>
          </div>
        )}

        {phase === "error" && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3.5">
            <div className="mb-1 flex items-center gap-2 text-sm font-medium text-destructive">
              <AlertTriangle className="size-3.5" />
              Run stopped
            </div>
            <p className="mb-3 text-xs text-muted-foreground">{errorMessage}</p>
            <Link href="/" className="text-xs font-medium text-foreground underline underline-offset-2">
              Start over
            </Link>
          </div>
        )}

        {phase === "done" && (
          <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3.5 text-sm text-emerald-300">
            Run complete — the preview on the right is the real build.
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import type { AssetPlanEntry, BlackboardAsset, RunEvent, Section } from "@/lib/api";
import { AssetTray } from "@/components/asset-tray";

/**
 * What the workspace shows while the site is being made.
 *
 * The main pane used to hold the string "Building preview…" for the entire
 * length of a run — several minutes, one static label, no evidence anything
 * was happening. Everything needed to do better was already on the wire and
 * being thrown away: `compose` writes the whole page plan to the blackboard
 * before a single section is built, and BUILD emits one event per section as
 * it lands. So the plan is drawn first, at the proportions it will actually
 * have, and the sections fill in against it top to bottom.
 *
 * Nothing here is invented for effect. Every block's height comes from its
 * archetype, its inset from `width`, its tint from `ground`, and the one
 * section marked `carries_signature` is the one the design agent chose — the
 * page's shape is legible before the page exists.
 */

/** Rough drawn height per archetype, so the silhouette has real rhythm
 *  rather than nine identical bars. Falls back to a mid height. */
const ARCHETYPE_HEIGHT: Record<string, number> = {
  "utility-bar": 26,
  nav: 26,
  footer: 74,
  hero: 190,
  "split-hero": 190,
  "feature-grid": 132,
  "logo-wall": 60,
  "stat-band": 72,
  "quote-block": 96,
  "pricing-table": 158,
  faq: 118,
  cta: 88,
};

function heightFor(s: Section): number {
  const key = (s.archetype || s.blueprint_id || "").toLowerCase();
  for (const [k, v] of Object.entries(ARCHETYPE_HEIGHT)) {
    if (key.includes(k)) return v;
  }
  return 110;
}

/** `width` is compose's vocabulary, not Tailwind's — map it to an inset. */
const WIDTH_INSET: Record<string, string> = {
  full: "0%",
  bleed: "0%",
  wide: "4%",
  container: "10%",
  narrow: "20%",
  tight: "26%",
};

const GROUND_TINT: Record<string, string> = {
  page: "bg-white/[0.04]",
  raised: "bg-white/[0.08]",
  inverted: "bg-white/[0.14]",
  accent: "bg-indigo-300/15",
  ink: "bg-white/[0.02]",
};

/**
 * Which sections BUILD has finished, read off the event stream.
 *
 * The builder yields `"{section.id}: {n} loc"` per section and
 * `"{section.id}: already built — kept"` for one it is reusing, so the id is
 * always the token before the first colon. Parsing the message is doing more
 * work than reading a field would, but the field does not exist — `data` is
 * empty on these events — and this needs no backend change to work.
 */
function builtIdsFrom(events: RunEvent[]): Set<string> {
  const done = new Set<string>();
  for (const e of events) {
    if (e.stage !== "build" || e.kind !== "progress") continue;
    const id = e.message.split(":")[0]?.trim();
    if (id) done.add(id);
  }
  return done;
}

export function BuildCanvas({
  sections,
  events,
  stage,
  headline,
  detail,
  assetPlan = [],
  madeAssets = [],
  projectId = "",
}: {
  sections: Section[];
  events: RunEvent[];
  /** The stage the run is actually in, for the status line. */
  stage: string;
  headline: string;
  detail?: string;
  assetPlan?: AssetPlanEntry[];
  madeAssets?: BlackboardAsset[];
  projectId?: string;
}) {
  const built = useMemo(() => builtIdsFrom(events), [events]);

  // The section currently under construction is the first one not yet built.
  // During earlier stages nothing is built, so nothing is marked active and
  // the plan reads as a plan.
  const activeId = useMemo(() => {
    if (stage !== "build") return null;
    return sections.find((s) => !built.has(s.id))?.id ?? null;
  }, [sections, built, stage]);

  const doneCount = sections.filter((s) => built.has(s.id)).length;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-baseline justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-2.5">
          <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">{headline}</span>
        </div>
        {sections.length > 0 && (
          <span className="text-xs tabular-nums text-muted-foreground">
            {doneCount} of {sections.length} sections
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        {sections.length === 0 ? (
          // Before compose there is no plan to draw yet. Say what is
          // happening rather than showing an empty frame.
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <div className="h-1 w-40 overflow-hidden rounded-full bg-muted/40">
              <div className="h-full w-1/3 animate-[canvas-sweep_1.6s_ease-in-out_infinite] rounded-full bg-foreground/50" />
            </div>
            <p className="text-sm text-muted-foreground">{detail ?? headline}</p>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-3xl">
            {/* The page, drawn at its own proportions. */}
            <div className="overflow-hidden rounded-xl border border-border bg-black/25 p-2 shadow-2xl shadow-black/40">
              {sections.map((s) => {
                const isBuilt = built.has(s.id);
                const isActive = s.id === activeId;
                const inset = WIDTH_INSET[(s.width || "container").toLowerCase()] ?? "10%";
                return (
                  <div
                    key={s.id}
                    className="relative mb-1 last:mb-0"
                    style={{ paddingLeft: inset, paddingRight: inset }}
                  >
                    <div
                      className={cn(
                        "relative flex items-center justify-between gap-3 overflow-hidden rounded-md px-3 transition-all duration-700",
                        GROUND_TINT[(s.ground || "page").toLowerCase()] ?? "bg-white/[0.04]",
                        isBuilt
                          ? "opacity-100 ring-1 ring-white/10"
                          : isActive
                            ? "opacity-90 ring-1 ring-indigo-300/40"
                            : "opacity-35"
                      )}
                      style={{ height: heightFor(s) }}
                    >
                      {/* A sweep across the section being built right now.
                          Transform-only, so it stays on the compositor. */}
                      {isActive && (
                        <span
                          aria-hidden="true"
                          className="pointer-events-none absolute inset-y-0 -left-full w-1/2 animate-[canvas-sweep_1.8s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent"
                        />
                      )}

                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-xs font-medium text-foreground/90">
                            {s.id}
                          </span>
                          {s.carries_signature && (
                            <Sparkles className="size-3 shrink-0 text-indigo-300" />
                          )}
                        </div>
                        {s.archetype && (
                          <p className="truncate text-[11px] text-muted-foreground">
                            {s.archetype}
                          </p>
                        )}
                      </div>

                      <span className="shrink-0">
                        {isBuilt ? (
                          <Check className="size-3.5 text-emerald-400" />
                        ) : isActive ? (
                          <Loader2 className="size-3.5 animate-spin text-indigo-300" />
                        ) : null}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Why the section being built looks the way it does. This is
                compose's own sentence, not a generated caption. */}
            {activeId && (
              <p className="mx-auto mt-4 max-w-xl text-center text-xs leading-relaxed text-muted-foreground">
                {sections.find((s) => s.id === activeId)?.contrast ?? detail ?? ""}
              </p>
            )}

            {/* The imagery, from the moment it is decided. During the assets
                stage this is the thing actually happening, and it is what
                the user was asked about one gate ago. */}
            <AssetTray
              plan={assetPlan}
              made={madeAssets}
              events={events}
              projectId={projectId}
            />
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";

import {
  assetUrl,
  type Direction,
  type GateInfo,
  type GateOption,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

/**
 * What the run is waiting on a human to decide.
 *
 * Renders in two places. Until something is built there is no preview to
 * show, so the design gate takes the main pane — the specimens are the
 * decision, and judging three palettes side by side in a 380px column is
 * strictly worse than judging them across the full width. Once a build
 * exists the preview owns that space and the remaining gate is two buttons,
 * which sit fine in the sidebar.
 */
export function GatePanel({
  gate,
  directions,
  layout,
  onAnswerGate,
}: {
  gate: GateInfo;
  directions: Direction[] | null;
  layout: "wide" | "compact";
  onAnswerGate: (choice: string | number, note?: string) => void;
}) {
  const [note, setNote] = useState("");
  const wide = layout === "wide";

  // Gate options carry the specimens and the "none of these" escape hatch;
  // GET /directions does not, so prefer options and fall back only if the
  // gate somehow arrived without them.
  const options: GateOption[] = gate.options?.length
    ? gate.options
    : (directions ?? []).map((d) => ({
        index: d.index,
        signature: d.signature,
        atmosphere: d.atmosphere,
        type: d.type,
        specimen: null,
      }));

  const sourcesSpecimen =
    gate.artifacts?.find((a) => a.includes("sources.png")) ?? null;
  const isDesignGate = gate.gate === "gate:design";

  return (
    <div
      className={cn(
        wide
          ? "mx-auto w-full max-w-5xl"
          : "rounded-xl border border-border bg-secondary/40 p-3.5"
      )}
    >
      <p
        className={cn(
          "text-foreground",
          wide ? "mb-5 text-lg font-medium tracking-tight" : "mb-3 text-sm"
        )}
      >
        {gate.question}
      </p>

      {/* The palettes measured from the reference sites — context for the
          choice, not one of the choices. */}
      {sourcesSpecimen && (
        <div className={wide ? "mb-6" : "mb-3"}>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">
            Your reference sites
          </p>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {/* The specimen is rendered 1800x1400 with the swatch rows in
              the top third; shown whole it buries the actual choices below
              the fold. Cap the height and crop from the top. */}
          <img
            src={assetUrl(sourcesSpecimen)}
            alt="Colours measured from the reference sites"
            className={cn(
              "w-full rounded-lg border border-border object-cover object-top",
              wide ? "max-h-72" : "max-h-44"
            )}
          />
        </div>
      )}

      {isDesignGate ? (
        <div
          className={cn(
            "grid gap-3",
            wide ? "grid-cols-1 lg:grid-cols-3 lg:items-start" : "grid-cols-1"
          )}
        >
          {options.map((o, i) => {
            const isOther = o.index === -1 || o.choice === "other";

            if (isOther) {
              return (
                <div
                  key="other"
                  className={cn(
                    "rounded-lg border border-dashed border-border p-3",
                    wide && "lg:col-span-3"
                  )}
                >
                  <p className="text-sm font-medium text-foreground">
                    {o.signature ?? "None of these"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{o.atmosphere}</p>
                  <div className={cn(wide && "flex items-start gap-2")}>
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={2}
                      placeholder="darker, warmer, less green…"
                      className="mt-2 w-full resize-none rounded-md border border-input bg-transparent px-2 py-1.5 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className={cn("mt-2 shrink-0", !wide && "block")}
                      // The backend 400s on an empty note, so gate the button
                      // rather than letting the request fail.
                      disabled={!note.trim()}
                      onClick={() => onAnswerGate("other", note.trim())}
                    >
                      Propose three new directions
                    </Button>
                  </div>
                </div>
              );
            }

            return (
              <button
                key={o.index ?? i}
                type="button"
                onClick={() => onAnswerGate(o.index ?? i)}
                className="group/dir flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card/40 text-left transition-colors hover:border-ring hover:bg-card"
              >
                {/* The rendered palette and type. This is the part a
                    non-designer can actually judge. */}
                {o.specimen && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={assetUrl(o.specimen)}
                    alt={o.signature ?? `Direction ${(o.index ?? i) + 1}`}
                    className="w-full border-b border-border"
                  />
                )}
                <div className={cn("flex flex-1 flex-col p-3", wide && "p-4")}>
                  <p className="text-sm font-medium text-foreground">{o.signature}</p>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                    {o.atmosphere}
                  </p>
                  {o.type && (
                    <p className="mt-auto pt-2 text-xs text-muted-foreground">{o.type}</p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(options.length ? options : [{ choice: "approve", label: "Approve" }]).map(
            (o, i) => (
              <Button
                key={i}
                type="button"
                variant={i === 0 ? "default" : "outline"}
                size="sm"
                onClick={() => onAnswerGate(o.choice ?? "approve")}
              >
                {String(o.label ?? o.choice ?? "Approve")}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  );
}

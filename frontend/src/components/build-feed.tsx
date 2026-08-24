"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { AlertTriangle, Check, CircleDashed, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Direction, GateInfo, RunEvent } from "@/lib/api";
import type { Source } from "@/lib/sources";
import { SparrowMark } from "@/components/sparrow-mark";
import { SourceCard } from "@/components/source-card";
import { Button } from "@/components/ui/button";

// Matches backend/src/sparrow/orchestrator.py's Stage enum, in order —
// needed to infer "done" for stages that end via a gate Halt rather than
// their own kind="done" event (design and verify never emit one; they stop
// at gate:design / gate:preview instead).
const FULL_ORDER = [
  "brief", "gate:brief", "sources", "design", "gate:design",
  "assets", "build", "verify", "gate:preview", "done",
];

const DISPLAY_STAGES: { key: string; label: string }[] = [
  { key: "brief", label: "Brief" },
  { key: "sources", label: "Sources" },
  { key: "design", label: "Design" },
  { key: "assets", label: "Assets" },
  { key: "build", label: "Build" },
  { key: "verify", label: "Verify" },
];

type StageStatus = "pending" | "active" | "done" | "failed";

function stageStatus(stageKey: string, events: RunEvent[]): StageStatus {
  const idx = FULL_ORDER.indexOf(stageKey);
  const own = events.filter((e) => e.stage === stageKey);
  if (own.some((e) => e.kind === "failed")) return "failed";
  if (events.some((e) => FULL_ORDER.indexOf(e.stage) > idx)) return "done";
  if (own.some((e) => e.kind === "done")) return "done";
  if (own.length > 0) return "active";
  return "pending";
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
  source,
  phase,
  events,
  spent,
  gate,
  directions,
  errorMessage,
  onAnswerGate,
}: {
  prompt: string;
  urls: string[];
  source: Source | null;
  phase: "loading" | "interview" | "create" | "run" | "gate" | "done" | "error";
  events: RunEvent[];
  spent: number;
  gate: GateInfo | null;
  directions: Direction[] | null;
  errorMessage: string | null;
  onAnswerGate: (choice: string | number, note?: string) => void;
}) {
  const logRef = useRef<HTMLDivElement>(null);

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

        {source && (
          <div className="mb-4">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Inspiration</p>
            <SourceCard source={source} />
          </div>
        )}

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
                  {STATUS_ICON[stageStatus(key, events)]}
                  <span
                    className={cn(
                      stageStatus(key, events) === "pending"
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

        {phase === "gate" && gate?.awaiting && (
          <div className="rounded-xl border border-border bg-secondary/40 p-3.5">
            <p className="mb-3 text-sm text-foreground">{gate.question}</p>

            {gate.gate === "gate:design" && directions ? (
              <div className="flex flex-col gap-2">
                {directions.map((d) => (
                  <button
                    key={d.index}
                    type="button"
                    onClick={() => onAnswerGate(d.index)}
                    className="rounded-lg border border-border bg-card/40 p-3 text-left transition-colors hover:bg-card"
                  >
                    <p className="text-sm font-medium text-foreground">{d.signature}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{d.atmosphere}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{d.type}</p>
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(gate.options?.length
                  ? gate.options
                  : [{ choice: "approve", label: "Approve" }]
                ).map((o, i) => (
                  <Button
                    key={i}
                    type="button"
                    variant={i === 0 ? "default" : "outline"}
                    size="sm"
                    onClick={() => onAnswerGate(o.choice ?? "approve")}
                  >
                    {String(o.label ?? o.choice ?? "Approve")}
                  </Button>
                ))}
              </div>
            )}
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

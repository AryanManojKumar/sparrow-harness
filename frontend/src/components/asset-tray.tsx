"use client";

import { useMemo } from "react";
import { Check, Film, Image as ImageIcon, Loader2, Minus, Stamp, Upload } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  producedFileUrl,
  type AssetKind,
  type AssetPlanEntry,
  type BlackboardAsset,
  type RunEvent,
} from "@/lib/api";

/**
 * Every asset the run intends to make or use, and where each one is.
 *
 * The plan is written at the asset gate; the assets stage then works through
 * it, one event per slot. Before this, none of that reached the screen: the
 * user answered "generate" for six images and a video, watched a stage row
 * spin for several minutes, and then had to open the built site to find out
 * which of them actually exist. Here the same list is drawn as soon as it is
 * decided, each slot moves through queued → generating → ready as its event
 * arrives, and the finished file is shown in place — so what was made is
 * known before the build, not discovered after it.
 */

type Status = "queued" | "generating" | "ready" | "skipped" | "wordmark";

const KIND_ICON: Record<AssetKind, React.ReactNode> = {
  logo: <Stamp className="size-3" />,
  image: <ImageIcon className="size-3" />,
  video: <Film className="size-3" />,
};

/** Which slots the assets stage has finished, read off its events.
 *
 * Every per-asset message the stage yields starts with the asset id, so the
 * id is the first token; the verb after it says what happened. Parsed here
 * rather than carried in `data` because `data` is empty on these events. */
function statusFromEvents(events: RunEvent[]): {
  done: Set<string>;
  started: boolean;
} {
  const done = new Set<string>();
  let started = false;
  for (const e of events) {
    if (e.stage !== "assets") continue;
    started = true;
    const m = e.message;
    const id = m.match(/^([\w-]+)[:\s]/)?.[1];
    if (!id) continue;
    if (
      /\bgenerated\b/.test(m) ||
      /used as it is/.test(m) ||
      /restyled from your file/.test(m) ||
      /shipping your own/.test(m) ||
      /substituted out of your/.test(m) ||
      /— kept\b/.test(m) ||
      /\bskipped\b/.test(m)
    ) {
      done.add(id);
    }
  }
  return { done, started };
}

export function AssetTray({
  plan,
  made,
  events,
  projectId,
  compact = false,
}: {
  plan: AssetPlanEntry[];
  made: BlackboardAsset[];
  events: RunEvent[];
  projectId: string;
  /** Sidebar layout — a vertical list with small previews. */
  compact?: boolean;
}) {
  const { done, started } = useMemo(() => statusFromEvents(events), [events]);
  const madeById = useMemo(() => new Map(made.map((a) => [a.id, a])), [made]);

  const rows = useMemo(
    () =>
      plan.map((p) => {
        const kind: AssetKind = p.kind ?? "image";
        const out = madeById.get(p.id);
        let status: Status;
        if (p.decision === "skip") status = "skipped";
        else if (p.decision === "wordmark") status = "wordmark";
        else if (out || done.has(p.id)) status = "ready";
        else if (started) status = "generating";
        else status = "queued";
        return { ...p, kind, out, status };
      }),
    [plan, madeById, done, started]
  );

  if (rows.length === 0) return null;

  const counts = rows.reduce(
    (acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }),
    {} as Partial<Record<Status, number>>
  );
  const videos = rows.filter((r) => r.kind === "video" && r.status !== "skipped").length;

  const summary = [
    counts.ready && `${counts.ready} ready`,
    counts.generating && `${counts.generating} generating`,
    counts.queued && `${counts.queued} queued`,
    counts.skipped && `${counts.skipped} left out`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className={cn(compact ? "" : "mx-auto mt-6 w-full max-w-3xl")}>
      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-xs font-medium text-muted-foreground">
          {compact ? "What was made" : "Assets"}
          {videos > 0 && (
            <span className="ml-1.5 font-normal opacity-70">
              · includes {videos === 1 ? "a video" : `${videos} videos`}
            </span>
          )}
        </p>
        <span className="text-[11px] tabular-nums text-muted-foreground">{summary}</span>
      </div>

      <div
        className={cn(
          compact
            ? "flex flex-col gap-1.5"
            : "grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4"
        )}
      >
        {rows.map((r) => (
          <AssetCell key={r.id} row={r} projectId={projectId} compact={compact} />
        ))}
      </div>
    </div>
  );
}

function AssetCell({
  row,
  projectId,
  compact,
}: {
  row: AssetPlanEntry & { kind: AssetKind; out?: BlackboardAsset; status: Status };
  projectId: string;
  compact: boolean;
}) {
  const { id, section_id, kind, out, status, decision } = row;
  // NOT the preview URL. The preview is the static export, which BUILD
  // writes after this stage is over; for the minutes in which these files
  // are being made, that URL 404s and every ready slot showed an empty box.
  const src = out ? producedFileUrl(projectId, out.path) : null;

  const preview = (
    <div
      className={cn(
        "relative shrink-0 overflow-hidden rounded-md bg-black/30",
        compact ? "size-11" : "aspect-[4/3] w-full"
      )}
    >
      {status === "ready" && src ? (
        kind === "video" ? (
          // First frame only — `preload="metadata"` fetches the header, not
          // the file, and nothing autoplays. A tray is not a place for five
          // looping videos.
          <video
            src={src}
            muted
            playsInline
            preload="metadata"
            className="size-full object-cover"
          />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- served by the sparrow API
          <img
            src={src}
            alt=""
            loading="lazy"
            decoding="async"
            className={cn("size-full", kind === "logo" ? "object-contain p-1.5" : "object-cover")}
          />
        )
      ) : (
        <div className="flex size-full items-center justify-center text-muted-foreground/60">
          {status === "generating" ? (
            <Loader2 className="size-4 animate-spin text-indigo-300/80" />
          ) : status === "skipped" ? (
            <Minus className="size-4" />
          ) : status === "wordmark" ? (
            <Stamp className="size-4" />
          ) : decision === "upload" ? (
            <Upload className="size-4" />
          ) : (
            KIND_ICON[kind]
          )}
        </div>
      )}
      {status === "ready" && (
        <span className="absolute right-1 top-1 rounded-full bg-black/60 p-0.5 text-emerald-300">
          <Check className="size-2.5" />
        </span>
      )}
      {kind === "video" && (
        <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 py-0.5 text-[9px] font-medium uppercase tracking-wide text-white/90">
          video
        </span>
      )}
    </div>
  );

  const label = (
    <div className="min-w-0">
      <p className="flex items-center gap-1 truncate text-[11px] font-medium text-foreground/90">
        <span className="text-muted-foreground">{KIND_ICON[kind]}</span>
        {id}
      </p>
      <p className="truncate text-[10px] text-muted-foreground">
        {section_id} ·{" "}
        {status === "ready"
          ? out?.provenance === "user_supplied"
            ? "your file"
            : "generated"
          : status === "generating"
            ? decision === "upload"
              ? "preparing your file"
              : "generating…"
            : status === "skipped"
              ? "left out"
              : status === "wordmark"
                ? "wordmark"
                : decision === "upload"
                  ? "your file, queued"
                  : "queued"}
      </p>
    </div>
  );

  return compact ? (
    <div className="flex items-center gap-2.5 rounded-lg border border-border bg-card/30 p-1.5">
      {preview}
      {label}
    </div>
  ) : (
    <div
      className={cn(
        "flex flex-col gap-1.5 rounded-lg border bg-card/30 p-1.5 transition-opacity",
        status === "skipped" ? "border-border opacity-50" : "border-border",
        status === "generating" && "ring-1 ring-indigo-300/30"
      )}
    >
      {preview}
      {label}
    </div>
  );
}

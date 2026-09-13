"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowUpRight, Check, CircleDashed, Hourglass, Loader2 } from "lucide-react";

import { isWaitingOnHuman, previewUrl, thumbUrl, type ProjectSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

// The thumbnail is a still, served by GET /projects/{id}/thumb.
//
// It used to be the real export in an iframe, scaled down — always current by
// construction, no capture step to go stale. What that actually cost: every
// card is a full Next.js site booting React, Motion, fonts and images, the
// listing renders all of them, and IntersectionObserver only delayed the
// mount rather than ever unmounting one. Nineteen projects meant nineteen
// live websites in the tab and a home screen that dropped frames on scroll.
// A card wants a picture, so it now gets a picture: the endpoint renders one
// viewport of the export with Playwright the first time it is asked and
// caches it on disk, so the cost is one browser launch per project ever.

function relativeTime(seconds?: number): string {
  if (!seconds) return "";
  const diff = Date.now() / 1000 - seconds;
  if (diff < 90) return "just now";
  const mins = Math.round(diff / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(seconds * 1000).toLocaleDateString();
}

/** "gate:design" → "design". Non-gate stages pass through unchanged. */
function stageLabel(stage?: string): string {
  if (!stage) return "";
  if (stage === "done") return "Done";
  const bare = stage.replace(/^gate:/, "");
  return bare.charAt(0).toUpperCase() + bare.slice(1);
}

export function ProjectCard({ project }: { project: ProjectSummary }) {
  const {
    project_id,
    readable,
    reason,
    product_name,
    category,
    stage,
    sections = 0,
    built = 0,
    has_preview,
    running,
    updated_at,
  } = project;

  // product_name is empty on projects that predate the identity work; the
  // directory name is the only other thing guaranteed to be there.
  const title = product_name?.trim() || project_id;
  // Executing on the server right now. Neither "needs you" nor "stopped":
  // the stage field alone cannot tell a run in progress from one that died
  // at the same stage, and reading it as the latter is what showed
  // "Stopped at sources" over a run that was extracting sources.
  const isRunning = Boolean(running);
  const needsYou = !isRunning && isWaitingOnHuman(stage);
  const isDone = stage === "done";
  // An export on disk is the whole condition. It used to also require
  // `built > 0`, on the theory that an export with no built sections is the
  // bare scaffold and would thumbnail as an empty dark rectangle.
  //
  // `built` counts sections the BLACKBOARD records as built, and it
  // under-reports badly on anything written before per-section status was
  // recorded: measured across the current projects, twelve of seventeen
  // exports reported 0 built sections while holding a complete, finished
  // page — the same drift `_infer_stage` exists to paper over on the server.
  // So the guard was hiding real sites behind "Stopped at …" placeholders.
  //
  // The server is the better judge now: it renders the still and 404s when
  // it cannot, and `onError` below turns that into the placeholder. Ask for
  // the picture and let the answer decide.
  const hasThumb = Boolean(has_preview);

  // Where the card goes on click, by stage. Opening a project must never
  // trigger /advance — that is billable, and a side-effect spend on a click
  // is exactly what this routing exists to prevent.
  //   done | gate:preview  -> the built site, no API call at all
  //   gate:*               -> the workspace, which reads the open question
  //   anything else        -> the workspace, which offers Resume and waits
  const goesToPreview = (isDone || stage === "gate:preview") && Boolean(has_preview);
  const workspaceHref =
    `/build?id=${encodeURIComponent(project_id)}&resume=1` +
    // Saves the workspace guessing whether an export exists; without it a
    // resumed project sits on "Building preview…" with a finished site.
    (has_preview ? "&preview=1" : "");
  const href = goesToPreview ? previewUrl(project_id) : workspaceHref;
  const opensExternally = goesToPreview;

  // A still can 404 — a project built before the capture step, or one whose
  // export cannot be rendered. Falling back to the same panel the unbuilt
  // cards use keeps a missing image from reading as a broken card.
  const [thumbFailed, setThumbFailed] = useState(false);
  const showThumb = hasThumb && !thumbFailed;

  if (!readable) {
    return (
      <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-card/20 opacity-60">
        <div className="flex aspect-[16/10] items-center justify-center border-b border-border bg-black/20">
          <AlertTriangle className="size-5 text-muted-foreground" />
        </div>
        <div className="p-3.5">
          <p className="truncate text-sm font-medium text-foreground">{project_id}</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {reason ?? "Written by an older version — can't be read."}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">{relativeTime(updated_at)}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="group/card flex flex-col overflow-hidden rounded-xl border border-border bg-card/30 transition-colors hover:border-ring/60 hover:bg-card/60">
      <a
        href={href}
        {...(opensExternally ? { target: "_blank", rel: "noreferrer" } : {})}
        className="block"
      >
        <div className="relative aspect-[16/10] overflow-hidden border-b border-border bg-black/30">
          {showThumb ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element -- served
                  by the sparrow API, not a Next-optimisable route */}
              <img
                src={thumbUrl(project_id)}
                alt=""
                aria-hidden="true"
                loading="lazy"
                decoding="async"
                onError={() => setThumbFailed(true)}
                className="size-full object-cover object-top transition-transform duration-500 group-hover/card:scale-[1.03]"
              />
              {/* Keeps the still from reading as an interactive page and
                  seats it against the card's own ground. */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
            </>
          ) : (
            // No build yet, so there is nothing to show — say where the run
            // actually got to instead of offering a link that goes nowhere.
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              {/* A spinner only when something is actually running — on a
                  parked project it would imply work that is not happening. */}
              {isRunning ? (
                <Loader2 className="size-5 animate-spin text-indigo-300/80" />
              ) : needsYou ? (
                <Hourglass className="size-5 text-amber-300/80" />
              ) : (
                <CircleDashed className="size-5" />
              )}
              <p className={cn("text-xs", needsYou && "text-amber-300/90", isRunning && "text-indigo-200/90")}>
                {isRunning
                  ? `Running · ${stageLabel(stage).toLowerCase()}`
                  : needsYou
                    ? "Waiting for you"
                    : `Stopped at ${stageLabel(stage).toLowerCase()}`}
              </p>
              {sections > 0 && (
                <div className="mt-1 flex w-24 gap-0.5">
                  {Array.from({ length: Math.min(sections, 12) }).map((_, i) => (
                    <span
                      key={i}
                      className={cn(
                        "h-1 flex-1 rounded-full",
                        i < built ? "bg-emerald-400/70" : "bg-muted"
                      )}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </a>

      <div className="flex items-start gap-2 p-3.5">
        <div className="min-w-0 flex-1">
          <a
            href={href}
            {...(opensExternally ? { target: "_blank", rel: "noreferrer" } : {})}
            className="block truncate text-sm font-medium text-foreground hover:underline"
          >
            {title}
          </a>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {category || "—"}
          </p>
          <div className="mt-2 flex items-center gap-2 text-xs">
            <span
              className={cn(
                "rounded-full px-1.5 py-0.5",
                isRunning
                  ? "bg-indigo-400/15 text-indigo-200"
                  : needsYou
                    ? "bg-amber-400/15 text-amber-300"
                    : isDone
                      ? "bg-emerald-400/15 text-emerald-300"
                      : "bg-muted text-muted-foreground"
              )}
            >
              {isRunning ? (
                <span className="inline-flex items-center gap-1">
                  <Loader2 className="size-3 animate-spin" /> Running
                </span>
              ) : needsYou ? "Needs you" : isDone ? (
                <span className="inline-flex items-center gap-1">
                  <Check className="size-3" /> Done
                </span>
              ) : stageLabel(stage)}
            </span>
            {sections > 0 && (
              <span className="text-muted-foreground">
                {built}/{sections} built
              </span>
            )}
            <span className="ml-auto shrink-0 text-muted-foreground">
              {relativeTime(updated_at)}
            </span>
          </div>
        </div>
      </div>

      {/* The cover already covers one of these; offer the other, so a
          project stopped at the preview gate can still be answered and a
          finished one can still be reopened in the workspace. */}
      {goesToPreview ? (
        <Link
          href={workspaceHref}
          className="flex items-center justify-center gap-1 border-t border-border py-2 text-xs text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover/card:opacity-100"
        >
          {isRunning ? "Watch it run" : needsYou ? "Answer the question" : "Open the workspace"}
        </Link>
      ) : (
        has_preview && (
          <a
            href={previewUrl(project_id)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-center gap-1 border-t border-border py-2 text-xs text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover/card:opacity-100"
          >
            Open the site <ArrowUpRight className="size-3" />
          </a>
        )
      )}
    </div>
  );
}

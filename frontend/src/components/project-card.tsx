"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowUpRight, Check, CircleDashed, Hourglass } from "lucide-react";

import { isWaitingOnHuman, previewUrl, type ProjectSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

// The thumbnail renders the real export in an iframe at desktop width and
// scales it down, rather than shipping a screenshot pipeline. It is always
// current by construction — no capture step to go stale — but it does mean a
// real page load per card, so the iframe only mounts once the card is near
// the viewport.
const FRAME_W = 1440;
const FRAME_H = 900;

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
    updated_at,
  } = project;

  // product_name is empty on projects that predate the identity work; the
  // directory name is the only other thing guaranteed to be there.
  const title = product_name?.trim() || project_id;
  const needsYou = isWaitingOnHuman(stage);
  const isDone = stage === "done";
  // has_preview only means an export directory exists. With nothing built
  // into it that export is the bare scaffold, which thumbnails as an empty
  // dark rectangle and reads as a broken card — so the thumbnail needs a
  // built section, while the "open the site" link still follows has_preview.
  const hasThumb = Boolean(has_preview) && built > 0;

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

  const shellRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.25);
  const [near, setNear] = useState(false);

  useEffect(() => {
    const el = shellRef.current;
    if (!el || !hasThumb) return;

    const ro = new ResizeObserver(([entry]) => {
      setScale(entry.contentRect.width / FRAME_W);
    });
    ro.observe(el);

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setNear(true);
          io.disconnect();
        }
      },
      { rootMargin: "300px" }
    );
    io.observe(el);

    return () => {
      ro.disconnect();
      io.disconnect();
    };
  }, [hasThumb]);

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
        <div
          ref={shellRef}
          className="relative aspect-[16/10] overflow-hidden border-b border-border bg-black/30"
        >
          {hasThumb ? (
            <>
              {near && (
                <iframe
                  src={previewUrl(project_id)}
                  title={`${title} preview`}
                  aria-hidden="true"
                  tabIndex={-1}
                  loading="lazy"
                  scrolling="no"
                  className="pointer-events-none absolute left-0 top-0 origin-top-left border-0"
                  style={{
                    width: FRAME_W,
                    height: FRAME_H,
                    transform: `scale(${scale})`,
                  }}
                />
              )}
              {/* Keeps the thumbnail from reading as an interactive page and
                  hides the seam while the frame is still painting. */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
            </>
          ) : (
            // No build yet, so there is nothing to show — say where the run
            // actually got to instead of offering a link that goes nowhere.
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              {/* Nothing is running here — a spinner would imply otherwise. */}
              {needsYou ? (
                <Hourglass className="size-5 text-amber-300/80" />
              ) : (
                <CircleDashed className="size-5" />
              )}
              <p className={cn("text-xs", needsYou && "text-amber-300/90")}>
                {needsYou ? "Waiting for you" : `Stopped at ${stageLabel(stage).toLowerCase()}`}
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
                needsYou
                  ? "bg-amber-400/15 text-amber-300"
                  : isDone
                    ? "bg-emerald-400/15 text-emerald-300"
                    : "bg-muted text-muted-foreground"
              )}
            >
              {needsYou ? "Needs you" : isDone ? (
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
          {needsYou ? "Answer the question" : "Open the workspace"}
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

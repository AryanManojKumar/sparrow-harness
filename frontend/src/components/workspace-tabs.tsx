"use client";

import Link from "next/link";
import { LayoutGrid, MessageSquare, Monitor, PanelLeft, Plus } from "lucide-react";

import { cn } from "@/lib/utils";
import { SparrowMark } from "@/components/sparrow-mark";

/** What the run is doing, as the tab's dot shows it. */
export type TabStatus = "loading" | "running" | "waiting" | "paused" | "live" | "error";

const DOT: Record<TabStatus, string> = {
  loading: "bg-muted-foreground/60",
  running: "bg-emerald-400 animate-pulse",
  waiting: "bg-amber-400",
  paused: "bg-muted-foreground",
  live: "bg-emerald-400",
  error: "bg-destructive",
};

const DOT_LABEL: Record<TabStatus, string> = {
  loading: "Loading",
  running: "Building",
  waiting: "Waiting for you",
  paused: "Paused",
  live: "Built",
  error: "Stopped",
};

/**
 * The workspace's top strip: Home, the open project as a tab, a new-site tab.
 *
 * No hooks and no state of its own, so the same markup is prerendered as the
 * loading shell and rendered again as the live bar — identical boxes in both,
 * which is what keeps the page from shifting when the workspace hydrates.
 * A client component only because its buttons take handlers.
 */
export function WorkspaceTabs({
  title,
  status,
  spent = 0,
  chatOpen = true,
  onToggleChat,
  mobileView = "chat",
  onMobileView,
}: {
  title: string;
  status: TabStatus;
  spent?: number;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  mobileView?: "chat" | "preview";
  onMobileView?: (v: "chat" | "preview") => void;
}) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-1 px-2 md:px-3">
      <Link
        href="/"
        prefetch={false}
        className="flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
      >
        <SparrowMark className="size-4" />
        <LayoutGrid className="size-3.5 max-sm:hidden" />
        <span className="max-sm:hidden">Home</span>
      </Link>

      <div
        // Fixed width, not max-width: the title changes once the project
        // loads, and a tab that resizes shoves the + beside it.
        className="flex h-8 w-40 min-w-0 shrink items-center gap-2 rounded-lg border border-border bg-card/70 px-3 text-sm text-foreground sm:w-56"
        title={`${title} · ${DOT_LABEL[status]}`}
      >
        <span className={cn("size-1.5 shrink-0 rounded-full", DOT[status])} aria-hidden="true" />
        <span className="truncate font-medium">{title}</span>
        <span className="sr-only">{DOT_LABEL[status]}</span>
      </div>

      <Link
        href="/"
        prefetch={false}
        aria-label="New site"
        title="New site"
        className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
      >
        <Plus className="size-4" />
      </Link>

      <div className="ml-auto flex items-center gap-1.5">
        {/* Always present (the shell shows it too), so the spend arriving
            changes its text, never the bar's layout. */}
        <span
          className="w-16 rounded-full border border-border py-1 text-center font-mono text-[11px] text-muted-foreground tabular-nums max-sm:hidden"
          title="Spent on model calls for this project"
        >
          ${spent.toFixed(2)}
        </span>

        {/* Phones get one pane at a time; this picks which. */}
        <div className="flex items-center rounded-lg border border-border bg-card/60 p-0.5 md:hidden">
          {(
            [
              { v: "chat", icon: MessageSquare, label: "Chat" },
              { v: "preview", icon: Monitor, label: "Preview" },
            ] as const
          ).map(({ v, icon: Icon, label }) => (
            <button
              key={v}
              type="button"
              onClick={() => onMobileView?.(v)}
              aria-pressed={mobileView === v}
              className={cn(
                "flex h-7 items-center gap-1 rounded-md px-2 text-xs transition-colors",
                mobileView === v ? "bg-muted text-foreground" : "text-muted-foreground"
              )}
            >
              <Icon className="size-3.5" /> {label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onToggleChat}
          aria-label={chatOpen ? "Hide chat" : "Show chat"}
          aria-pressed={!chatOpen}
          title={chatOpen ? "Hide chat" : "Show chat"}
          className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground max-md:hidden"
        >
          <PanelLeft className="size-4" />
        </button>

        <div className="flex size-8 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground">
          A
        </div>
      </div>
    </header>
  );
}

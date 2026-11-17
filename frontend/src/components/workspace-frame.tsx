import type { ReactNode, Ref } from "react";

import { cn } from "@/lib/utils";
import { WorkspaceTabs } from "@/components/workspace-tabs";

/**
 * The workspace before it knows anything: what the server sends while the
 * client renders, and what the client's first commit draws before the full
 * workspace renders as a transition. Same boxes as the live frame.
 */
export function WorkspaceShell() {
  return (
    <WorkspaceFrame
      tabs={<WorkspaceTabs title="Opening project…" status="loading" />}
      chat={
        <div className="flex h-full flex-col gap-3 px-4 py-4">
          <div className="h-16 animate-pulse rounded-xl bg-secondary/60" />
          <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
        </div>
      }
      main={
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          Loading the workspace…
        </div>
      }
    />
  );
}

/**
 * The workspace's boxes: tab bar on top, chat on the left, the page on the
 * right in an inset panel. Shared by the server-rendered loading shell and
 * the live workspace so the two are the same size by construction.
 *
 * Chat width is the CSS variable `--chat-w` (see globals.css), never React
 * state: dragging the divider writes the variable and nothing re-renders.
 * Phones show one pane at a time, picked in the tab bar.
 */
export function WorkspaceFrame({
  tabs,
  chat,
  main,
  divider,
  chatOpen = true,
  mobileView = "chat",
  resizing = false,
  chatRef,
}: {
  tabs: ReactNode;
  chat: ReactNode;
  main: ReactNode;
  divider?: ReactNode;
  chatOpen?: boolean;
  mobileView?: "chat" | "preview";
  /** While dragging, width follows the pointer with no easing. */
  resizing?: boolean;
  chatRef?: Ref<HTMLElement>;
}) {
  return (
    <div className="flex h-dvh flex-col">
      {tabs}
      <div className="flex min-h-0 flex-1 px-2 pb-2 md:px-3 md:pb-3">
        <aside
          ref={chatRef}
          aria-label="Chat"
          className={cn(
            "relative flex min-h-0 w-full shrink-0 flex-col overflow-hidden",
            mobileView === "chat" ? "max-md:flex" : "max-md:hidden",
            chatOpen ? "md:w-(--chat-w)" : "md:w-0",
            !resizing &&
              "md:transition-[width] md:duration-200 md:ease-out motion-reduce:transition-none"
          )}
        >
          {/* Fixed width inside, so collapsing slides the column away instead
              of reflowing its text at every frame of the animation. */}
          <div className="flex h-full min-h-0 w-full flex-col md:w-(--chat-w)">{chat}</div>
        </aside>
        {/* The gap is the divider's 8px whether or not there is one, so the
            shell and the live workspace put the panel in the same place. */}
        {chatOpen ? (divider ?? <div className="w-2 shrink-0 max-md:hidden" />) : null}
        <main
          className={cn(
            "relative min-h-0 min-w-0 flex-1 overflow-hidden rounded-xl border border-border bg-card/30",
            mobileView === "preview" ? "max-md:block" : "max-md:hidden"
          )}
        >
          {main}
        </main>
      </div>
    </div>
  );
}

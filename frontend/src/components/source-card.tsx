"use client";

import { X } from "lucide-react";

import type { Source } from "@/lib/sources";
import { cn } from "@/lib/utils";
import { Favicon } from "@/components/favicon";

/**
 * A reference site, collapsed to a clean attachment chip — the same idea as
 * pasting a large file into a chat and getting back a compact card instead
 * of a wall of text. Used both below the prompt box and, once a run starts,
 * in the chat feed — same component, same look, so the citation reads as
 * the same object carrying through rather than two different UI ideas.
 */
export function SourceCard({
  source,
  onRemove,
  className,
  onClickOverride,
}: {
  source: Source;
  onRemove?: () => void;
  className?: string;
  /** When set, clicking the card calls this instead of opening the URL —
   * used where the card is really an editable field (reference sites) and
   * a click means "let me edit this," not "take me to the site." */
  onClickOverride?: () => void;
}) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noreferrer"
      onClick={
        onClickOverride
          ? (e) => {
              e.preventDefault();
              onClickOverride();
            }
          : undefined
      }
      className={cn(
        "group/source flex items-center gap-3 rounded-xl border border-border bg-secondary/40 px-3 py-2.5 text-left transition-colors hover:bg-secondary/70",
        className
      )}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        <Favicon url={source.url} className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{source.title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {source.domain} · {source.description}
        </p>
      </div>
      {onRemove && (
        <button
          type="button"
          aria-label="Remove reference"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onRemove();
          }}
          className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="size-3.5" />
        </button>
      )}
    </a>
  );
}

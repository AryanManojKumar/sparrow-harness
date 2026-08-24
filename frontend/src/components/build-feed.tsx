"use client";

import { Check, CircleDashed, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { SparrowMark } from "@/components/sparrow-mark";
import { SourceCard } from "@/components/source-card";
import type { SectionState } from "@/lib/build-feed";
import type { Source } from "@/lib/sources";

const STATUS_ICON: Record<SectionState["status"], React.ReactNode> = {
  pending: <CircleDashed className="size-3.5 text-muted-foreground" />,
  building: <Loader2 className="size-3.5 animate-spin text-foreground" />,
  done: <Check className="size-3.5 text-emerald-400" />,
};

export function BuildFeed({
  prompt,
  sections,
  source,
}: {
  prompt: string;
  sections: SectionState[];
  source?: Source | null;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <SparrowMark className="size-4" />
        <span className="text-sm font-medium text-foreground">sparrow</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mb-2 rounded-xl bg-secondary/60 px-3.5 py-2.5 text-sm text-foreground">
          {prompt}
        </div>

        {/* Carries the same reference the prompt box attached — same card,
            same look, so it reads as one object moving forward with the
            run rather than two separate ideas. */}
        {source && (
          <div className="mb-4">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Sources</p>
            <SourceCard source={source} />
          </div>
        )}

        <p className="mb-3 text-xs font-medium text-muted-foreground">Building your site</p>
        <ul className="flex flex-col gap-2.5">
          {sections.map((s) => (
            <li key={s.name} className="flex items-center gap-2.5 text-sm">
              {STATUS_ICON[s.status]}
              <span
                className={cn(
                  s.status === "pending" ? "text-muted-foreground" : "text-foreground"
                )}
              >
                {s.name}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

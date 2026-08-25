"use client";

import { useRef, useState } from "react";
import { X } from "lucide-react";

import { hostnameOf, isHttpUrl } from "@/lib/urls";
import { SourceCard } from "@/components/source-card";
import { Input } from "@/components/ui/input";

/**
 * One reference-site slot. A plain input until it holds a real URL, then it
 * collapses into the same rich preview card everywhere else in the app uses
 * (favicon + title) — the link-preview look of pasting a URL into WhatsApp
 * or iMessage, rather than a bare text field sitting there once it's valid.
 * Click the card to edit it again.
 */
export function ReferenceSiteRow({
  value,
  onChange,
  onRemove,
}: {
  value: string;
  onChange: (next: string) => void;
  onRemove: () => void;
}) {
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const showCard = isHttpUrl(value) && !focused;

  if (showCard) {
    return (
      <SourceCard
        source={{
          id: value,
          title: hostnameOf(value),
          domain: hostnameOf(value),
          url: value,
          description: "Reference site",
        }}
        onRemove={onRemove}
        className="cursor-text"
        onClickOverride={() => inputRef.current?.focus()}
      />
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="https://…"
        className="h-9 text-sm"
      />
      <button
        type="button"
        aria-label="Remove reference"
        // onMouseDown, not onClick: the input's onBlur fires first on click
        // and re-renders this row as a card, so the click never lands.
        onMouseDown={(e) => {
          e.preventDefault();
          onRemove();
        }}
        className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}

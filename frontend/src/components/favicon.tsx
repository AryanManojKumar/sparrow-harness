"use client";

import { useState } from "react";
import { Link2 } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * A site's real favicon via Google's favicon service, falling back to a
 * generic link glyph if the domain is invalid or the icon fails to load —
 * the "small logo" a link preview (WhatsApp, iMessage, Slack) shows next to
 * the title, rather than a generic attachment icon for every source.
 */
export function Favicon({ url, className }: { url: string; className?: string }) {
  const [failed, setFailed] = useState(false);

  let host = "";
  try {
    host = new URL(url).hostname;
  } catch {
    // not a parseable URL — fall through to the glyph
  }

  if (failed || !host) {
    return <Link2 className={className} />;
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- one small icon
    // per source from an external favicon service; not worth next/image's
    // remote-pattern config for a fallback-prone, per-value icon.
    <img
      src={`https://www.google.com/s2/favicons?sz=64&domain=${encodeURIComponent(host)}`}
      alt=""
      className={cn("object-contain", className)}
      onError={() => setFailed(true)}
    />
  );
}

"use client";

import { useState } from "react";
import { ExternalLink, Monitor, RefreshCw, Smartphone, Tablet } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type Device = "desktop" | "tablet" | "mobile";

const FRAME_WIDTH: Record<Device, string> = {
  desktop: "100%",
  tablet: "768px",
  mobile: "390px",
};

export function PreviewPane({
  ready,
  src,
  waitingLabel = "Building preview…",
}: {
  ready: boolean;
  /** The run's `GET /projects/{id}/preview/` URL — drops straight into an iframe. */
  src?: string;
  waitingLabel?: string;
}) {
  const [device, setDevice] = useState<Device>("desktop");
  const [reloadKey, setReloadKey] = useState(0);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-1 rounded-lg border border-border bg-card/60 p-0.5">
          {(
            [
              { id: "desktop", icon: Monitor, label: "Desktop" },
              { id: "tablet", icon: Tablet, label: "Tablet" },
              { id: "mobile", icon: Smartphone, label: "Mobile" },
            ] as const
          ).map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setDevice(id)}
              aria-label={label}
              className={cn(
                "flex size-7 items-center justify-center rounded-md transition-colors",
                device === id
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="size-3.5" />
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Refresh preview"
            disabled={!ready || !src}
            onClick={() => setReloadKey((k) => k + 1)}
          >
            <RefreshCw className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            asChild
            className={cn((!ready || !src) && "pointer-events-none opacity-50")}
          >
            <a
              href={ready && src ? src : undefined}
              target="_blank"
              rel="noreferrer"
              aria-disabled={!ready || !src}
              aria-label="Open preview in a new tab"
            >
              <ExternalLink className="size-3.5" />
            </a>
          </Button>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center overflow-auto bg-black/20 p-6">
        {ready && src ? (
          <div
            className="h-full overflow-hidden rounded-xl border border-border bg-white shadow-2xl shadow-black/50 transition-[width] duration-300"
            style={{ width: FRAME_WIDTH[device] }}
          >
            <iframe
              key={reloadKey}
              src={src}
              title="Site preview"
              className="size-full border-0"
            />
          </div>
        ) : (
          <div
            className="flex h-full flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border text-muted-foreground transition-[width] duration-300"
            style={{ width: FRAME_WIDTH[device] }}
          >
            <div className="size-8 animate-pulse rounded-lg bg-muted" />
            <p className="text-sm">{waitingLabel}</p>
          </div>
        )}
      </div>
    </div>
  );
}

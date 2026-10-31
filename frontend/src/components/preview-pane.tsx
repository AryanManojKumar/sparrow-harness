"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ExternalLink,
  Globe,
  Monitor,
  RefreshCw,
  Smartphone,
  Tablet,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type Device = "desktop" | "tablet" | "mobile";

// The width the site is RENDERED at, not the width it is shown at. A desktop
// layout squeezed into a 1000px pane is the tablet layout — nav collapsed to a
// "Menu" button, type at its smaller step — which reads as "zoomed in". So
// the frame is laid out at the real width and scaled down to fit.
const DEVICE_WIDTH: Record<Device, number> = {
  desktop: 1440,
  tablet: 768,
  mobile: 390,
};

/** "/" → "Home", "/pricing/" → "Pricing", "/blog/first-post/" → "Blog / First post". */
export function pageName(path: string): string {
  const parts = path.split("/").filter(Boolean);
  if (!parts.length) return "Home";
  return parts
    .map((p) => {
      const words = p.replace(/[-_]+/g, " ");
      return words.charAt(0).toUpperCase() + words.slice(1);
    })
    .join(" / ");
}

export function PreviewPane({
  ready,
  src,
  waitingLabel = "Building preview…",
  version = 0,
  pages = [],
  path,
  navNonce = 0,
}: {
  ready: boolean;
  /** The site's root, e.g. `/projects/{id}/preview/`. Same-origin with the
   *  console (proxied by next.config), so the address bar can follow it. */
  src?: string;
  waitingLabel?: string;
  /** Bumped by the owner of the pane when the site changed underneath it. */
  version?: number;
  /** The site's pages, for the page switcher. */
  pages?: string[];
  /** A page to show, as a path under the site root ("/pricing/"). */
  path?: string;
  /** Bumped to (re)navigate to `path` even when it has not changed. */
  navNonce?: number;
}) {
  const [device, setDevice] = useState<Device>("desktop");
  const [reloadKey, setReloadKey] = useState(0);
  // The page the frame was asked to load, and the page it is actually on —
  // they differ as soon as the owner clicks a link inside the site.
  const [target, setTarget] = useState(path ?? "/");
  const [current, setCurrent] = useState(path ?? "/");
  const [menuOpen, setMenuOpen] = useState(false);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const stageRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<HTMLIFrameElement>(null);

  const base = (src ?? "").replace(/\/$/, "");

  useEffect(() => {
    if (!path) return;
    setTarget(path);
    setReloadKey((k) => k + 1);
  }, [path, navNonce]);

  useLayoutEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const r = entry.contentRect;
      setBox({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ready]);

  const width = DEVICE_WIDTH[device];
  const pad = 24;
  const scale = box.w ? Math.min(1, (box.w - pad * 2) / width) : 1;
  const frameH = box.h ? (box.h - pad * 2) / scale : 800;

  function onFrameLoad() {
    try {
      const loc = frameRef.current?.contentWindow?.location.pathname ?? "";
      if (base && loc.startsWith(base)) setCurrent(loc.slice(base.length) || "/");
    } catch {
      // Cross-origin (an API URL rather than the proxied one): the address
      // bar keeps showing the page that was asked for.
      setCurrent(target);
    }
  }

  function go(p: string) {
    setMenuOpen(false);
    setTarget(p);
    setReloadKey((k) => k + 1);
  }

  const live = ready && Boolean(src);
  const frameSrc = live ? `${base}${target === "/" ? "/" : target}` : undefined;
  const knownPages = pages.length ? pages : ["/"];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-border px-3 py-2">
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
              title={`${label} · ${DEVICE_WIDTH[id]}px`}
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

        <button
          type="button"
          aria-label="Back"
          disabled={!live}
          onClick={() => {
            try {
              frameRef.current?.contentWindow?.history.back();
            } catch {}
          }}
          className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40"
        >
          <ArrowLeft className="size-3.5" />
        </button>

        {/* The address bar: which page of the site is showing, and every page
            it has. A studio change can add a page the nav hides on a small
            screen; this is how the owner finds it. */}
        <div className="relative min-w-0 flex-1">
          <button
            type="button"
            disabled={!live}
            onClick={() => setMenuOpen((o) => !o)}
            className="flex h-8 w-full min-w-0 items-center gap-2 rounded-lg border border-border bg-card/60 px-3 text-left text-xs hover:bg-muted disabled:opacity-50"
          >
            <Globe className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="shrink-0 font-medium text-foreground">{pageName(current)}</span>
            <span className="truncate text-muted-foreground">{current}</span>
            <span className="ml-auto flex shrink-0 items-center gap-1 text-muted-foreground">
              {knownPages.length} page{knownPages.length === 1 ? "" : "s"}
              <ChevronDown className="size-3" />
            </span>
          </button>
          {menuOpen && (
            <div className="absolute left-0 right-0 top-9 z-30 overflow-hidden rounded-lg border border-border bg-card shadow-xl">
              {knownPages.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => go(p)}
                  className={cn(
                    "flex w-full items-center justify-between px-3 py-2 text-left text-xs hover:bg-muted",
                    p === current ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  <span className="font-medium">{pageName(p)}</span>
                  <span className="font-mono text-[10.5px]">{p}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Refresh preview"
            disabled={!live}
            onClick={() => setReloadKey((k) => k + 1)}
          >
            <RefreshCw className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            asChild
            className={cn(!live && "pointer-events-none opacity-50")}
          >
            <a
              href={live ? `${base}${current}` : undefined}
              target="_blank"
              rel="noreferrer"
              aria-disabled={!live}
              aria-label="Open preview in a new tab"
            >
              <ExternalLink className="size-3.5" />
            </a>
          </Button>
        </div>
      </div>

      <div ref={stageRef} className="relative flex-1 overflow-hidden bg-black/20">
        {live && box.w > 0 ? (
          <div
            className="absolute left-1/2 top-6 overflow-hidden rounded-xl border border-border bg-white shadow-2xl shadow-black/50"
            style={{
              width: width * scale,
              height: box.h - pad * 2,
              transform: "translateX(-50%)",
            }}
          >
            <iframe
              ref={frameRef}
              key={`${version}-${reloadKey}`}
              src={frameSrc}
              title="Site preview"
              onLoad={onFrameLoad}
              className="origin-top-left border-0"
              style={{ width, height: frameH, transform: `scale(${scale})` }}
            />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center p-6">
            <div
              className="flex h-full flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border text-muted-foreground"
              style={{ width: Math.min(width, Math.max(box.w - pad * 2, 0)) || "100%" }}
            >
              <div className="size-8 animate-pulse rounded-lg bg-muted" />
              <p className="text-sm">{waitingLabel}</p>
            </div>
          </div>
        )}
        {live && (
          <div className="pointer-events-none absolute bottom-2 right-3 rounded bg-black/50 px-1.5 py-0.5 font-mono text-[10px] text-white/70">
            {width}px · {Math.round(scale * 100)}%
          </div>
        )}
      </div>
    </div>
  );
}

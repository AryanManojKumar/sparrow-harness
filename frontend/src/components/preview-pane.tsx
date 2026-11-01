"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ExternalLink,
  Globe,
  Monitor,
  MousePointerClick,
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

/** An element the owner clicked in the preview, as the chat attaches it. */
export type PickedElement = {
  id: string;
  /** The page it is on, under the site root: "/pricing/". */
  page: string;
  tag: string;
  /** Its visible text, trimmed. */
  text: string;
  /** Short chip label: "h1 · Pricing for customer operations." */
  label: string;
  /** The top-level block of the page it sits in, described for the agent. */
  block: string;
  /** Its own markup, truncated — enough to find it in the source. */
  html: string;
};

// Inline pieces (a line-wrapping <span> inside a heading, an icon's <path>)
// are not what an owner means by "this": promote them to the nearest element
// that is — the heading, paragraph, button, link or image they belong to.
const MEANINGFUL = "h1,h2,h3,h4,h5,h6,p,a,button,li,img,video,figure,blockquote,label,input,textarea,select,table";
const INLINE = new Set(["SPAN", "STRONG", "EM", "B", "I", "SMALL", "BR", "SUP", "SUB", "MARK", "path", "svg", "g", "use", "circle", "rect", "line", "polyline"]);

function meaningful(el: Element): Element {
  if (!INLINE.has(el.tagName)) return el;
  return el.closest(MEANINGFUL) ?? el.closest("div,section,header,footer,nav,article") ?? el;
}

function describe(el: Element, page: string): PickedElement {
  const tag = el.tagName.toLowerCase();
  const text = ((el as HTMLElement).innerText || el.textContent || "").replace(/\s+/g, " ").trim();
  const alt = el.getAttribute("alt") || el.getAttribute("aria-label") || "";
  // The block: the ancestor that is a direct child of <main> (or <body>) —
  // the section the generator built as one component.
  let block: Element | null = el;
  while (block && block.parentElement && !["MAIN", "BODY"].includes(block.parentElement.tagName)) {
    block = block.parentElement;
  }
  let blockDesc = "the page";
  if (block && block.parentElement) {
    const siblings = Array.from(block.parentElement.children);
    const n = siblings.indexOf(block) + 1;
    const heading = block.querySelector("h1, h2, h3")?.textContent?.replace(/\s+/g, " ").trim();
    blockDesc = `block ${n} of ${siblings.length} on the page (a <${block.tagName.toLowerCase()}>${
      heading ? ` whose heading reads "${heading.slice(0, 90)}"` : ""
    })`;
  }
  const html = el.outerHTML.replace(/\s+/g, " ").slice(0, 1200);
  const shown = (text || alt || (tag === "img" ? el.getAttribute("src")?.split("/").pop() : "") || "").slice(0, 60);
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    page,
    tag,
    text: text.slice(0, 400),
    label: shown ? `${tag} · ${shown}` : tag,
    block: blockDesc,
    html,
  };
}

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
  onPick,
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
  /** Enables "Select": the owner clicks an element and it is handed here. */
  onPick?: (el: PickedElement) => void;
}) {
  const [device, setDevice] = useState<Device>("desktop");
  const [reloadKey, setReloadKey] = useState(0);
  // The page the frame was asked to load, and the page it is actually on —
  // they differ as soon as the owner clicks a link inside the site.
  const [target, setTarget] = useState(path ?? "/");
  const [current, setCurrent] = useState(path ?? "/");
  const [menuOpen, setMenuOpen] = useState(false);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const [selecting, setSelecting] = useState(false);
  // Bumped on every frame load, so the inspector re-binds after navigation.
  const [loadTick, setLoadTick] = useState(0);
  const pickRef = useRef(onPick);
  pickRef.current = onPick;
  const canPick = Boolean(onPick);
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

  // The inspector lives inside the site's own document (same-origin through
  // the proxy): a highlight box follows the pointer, a click is captured
  // before the site sees it — no link fires, no button runs — and the element
  // is described for the chat. Escape leaves the mode.
  useEffect(() => {
    if (!selecting || !canPick) return;
    let doc: Document | null = null;
    try {
      doc = frameRef.current?.contentDocument ?? null;
    } catch {
      doc = null;
    }
    if (!doc?.body) return;
    const d = doc;
    const hl = d.createElement("div");
    const tag = d.createElement("div");
    hl.style.cssText =
      "position:fixed;pointer-events:none;z-index:2147483647;border:2px solid #818cf8;" +
      "background:rgba(129,140,248,.10);border-radius:4px;transition:all 60ms ease-out;display:none";
    tag.style.cssText =
      "position:absolute;left:-2px;top:-22px;background:#818cf8;color:#fff;font:600 11px ui-monospace,monospace;" +
      "padding:2px 6px;border-radius:4px 4px 4px 0;white-space:nowrap";
    hl.appendChild(tag);
    d.body.appendChild(hl);
    const prevCursor = d.body.style.cursor;
    d.body.style.cursor = "crosshair";

    const move = (e: MouseEvent) => {
      const el = e.target ? meaningful(e.target as Element) : null;
      if (!el || el === d.body || el === d.documentElement) {
        hl.style.display = "none";
        return;
      }
      const r = el.getBoundingClientRect();
      hl.style.display = "block";
      hl.style.left = `${r.left}px`;
      hl.style.top = `${r.top}px`;
      hl.style.width = `${r.width}px`;
      hl.style.height = `${r.height}px`;
      tag.textContent = el.tagName.toLowerCase();
      tag.style.top = r.top < 24 ? "100%" : "-22px";
    };
    const swallow = (e: Event) => {
      e.preventDefault();
      e.stopPropagation();
    };
    const click = (e: MouseEvent) => {
      swallow(e);
      const el = e.target ? meaningful(e.target as Element) : null;
      if (!el || el === d.body) return;
      const page = (() => {
        const loc = d.location.pathname;
        return base && loc.startsWith(base) ? loc.slice(base.length) || "/" : current;
      })();
      pickRef.current?.(describe(el, page));
      setSelecting(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelecting(false);
    };
    d.addEventListener("mousemove", move, true);
    d.addEventListener("click", click, true);
    d.addEventListener("mousedown", swallow, true);
    d.addEventListener("keydown", key, true);
    window.addEventListener("keydown", key);
    return () => {
      d.removeEventListener("mousemove", move, true);
      d.removeEventListener("click", click, true);
      d.removeEventListener("mousedown", swallow, true);
      d.removeEventListener("keydown", key, true);
      window.removeEventListener("keydown", key);
      hl.remove();
      d.body.style.cursor = prevCursor;
    };
  }, [selecting, loadTick, canPick, base, current]);

  const width = DEVICE_WIDTH[device];
  const pad = 24;
  const scale = box.w ? Math.min(1, (box.w - pad * 2) / width) : 1;
  const frameH = box.h ? (box.h - pad * 2) / scale : 800;

  function onFrameLoad() {
    setLoadTick((t) => t + 1);
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
  // The query string only defeats any cache between here and the workshop;
  // the export ignores it. Without it a reload could show the build before.
  const frameSrc = live
    ? `${base}${target === "/" ? "/" : target}?v=${version}-${reloadKey}`
    : undefined;
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

        {onPick && (
          <button
            type="button"
            disabled={!live}
            onClick={() => setSelecting((v) => !v)}
            title="Select an element to talk about it (Esc to cancel)"
            className={cn(
              "flex h-7 items-center gap-1.5 rounded-md border px-2 text-xs transition-colors disabled:opacity-40",
              selecting
                ? "border-indigo-400/60 bg-indigo-500/15 text-indigo-200"
                : "border-border text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <MousePointerClick className="size-3.5" />
            {selecting ? "Click an element" : "Select"}
          </button>
        )}

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
            className={cn(
              "absolute left-1/2 top-6 flex flex-col overflow-hidden rounded-xl border bg-white shadow-2xl shadow-black/60 transition-[box-shadow,border-color]",
              selecting ? "border-indigo-400/70 ring-2 ring-indigo-400/30" : "border-white/10"
            )}
            style={{
              width: width * scale,
              height: box.h - pad * 2,
              transform: "translateX(-50%)",
            }}
          >
            {/* Window chrome, so the frame reads as a browser and not a panel. */}
            <div className="flex h-7 shrink-0 items-center gap-1.5 border-b border-black/10 bg-[#ececee] px-3">
              <span className="size-2.5 rounded-full bg-[#ff5f57]" />
              <span className="size-2.5 rounded-full bg-[#febc2e]" />
              <span className="size-2.5 rounded-full bg-[#28c840]" />
              <span className="mx-auto max-w-[60%] truncate rounded-md bg-white/80 px-3 py-0.5 text-center font-mono text-[10px] text-black/50">
                {pageName(current)} · {current}
              </span>
              <span className="w-[42px]" />
            </div>
            <iframe
              ref={frameRef}
              key={`${version}-${reloadKey}`}
              src={frameSrc}
              title="Site preview"
              onLoad={onFrameLoad}
              className="shrink-0 origin-top-left border-0"
              style={{ width, height: frameH - 28 / scale, transform: `scale(${scale})` }}
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

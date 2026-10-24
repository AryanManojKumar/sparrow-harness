"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ExternalLink,
  Loader2,
  Monitor,
  MousePointer2,
  RefreshCw,
  Smartphone,
  Tablet,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { editProject } from "@/lib/api";
import {
  PICKER_CHANNEL,
  parsePickerMessage,
  toEditElement,
  type PickedElement,
} from "@/lib/picker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Device = "desktop" | "tablet" | "mobile";

const FRAME_WIDTH: Record<Device, string> = {
  desktop: "100%",
  tablet: "768px",
  mobile: "390px",
};

export function PreviewPane({
  ready,
  src,
  projectId,
  waitingLabel = "Building preview…",
}: {
  ready: boolean;
  /** The run's `GET /projects/{id}/preview/` URL — drops straight into an iframe. */
  src?: string;
  projectId?: string;
  waitingLabel?: string;
}) {
  const [device, setDevice] = useState<Device>("desktop");
  const [reloadKey, setReloadKey] = useState(0);
  const [selecting, setSelecting] = useState(false);
  const [picked, setPicked] = useState<PickedElement | null>(null);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const origin = src ? new URL(src).origin : "";

  const postToFrame = useCallback(
    (type: string) => {
      const win = iframeRef.current?.contentWindow;
      if (!win || !origin) return;
      win.postMessage({ channel: PICKER_CHANNEL, type }, origin);
    },
    [origin]
  );

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (origin && event.origin !== origin) return;
      const msg = parsePickerMessage(event.data);
      if (!msg) return;
      if (msg.type === "ready" && selecting) postToFrame("select-enable");
      if (msg.type === "element-select") {
        setPicked(msg.payload);
        setError(null);
      }
      if (msg.type === "element-clear") setPicked(null);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [origin, selecting, postToFrame]);

  useEffect(() => {
    postToFrame(selecting ? "select-enable" : "select-disable");
    if (!selecting) {
      setPicked(null);
      setInstruction("");
      setError(null);
    }
  }, [selecting, postToFrame, reloadKey]);

  async function applyEdit() {
    if (!projectId || !picked || !instruction.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      await editProject(projectId, instruction.trim(), toEditElement(picked));
      setInstruction("");
      setPicked(null);
      setReloadKey((k) => k + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const canApply = Boolean(projectId && picked && instruction.trim() && !busy);

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
            variant={selecting ? "secondary" : "ghost"}
            size="sm"
            aria-pressed={selecting}
            aria-label="Select element"
            disabled={!ready || !src}
            onClick={() => setSelecting((on) => !on)}
            className={cn(selecting && "text-foreground")}
          >
            <MousePointer2 className="size-3.5" />
            Select
          </Button>
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
            className="relative h-full overflow-hidden rounded-xl border border-border bg-white shadow-2xl shadow-black/50 transition-[width] duration-300"
            style={{ width: FRAME_WIDTH[device] }}
          >
            <iframe
              ref={iframeRef}
              key={reloadKey}
              src={src}
              title="Site preview"
              className="size-full border-0"
            />
            {selecting && (
              <div className="absolute inset-x-0 bottom-0 z-10 border-t border-border bg-card/95 p-3 backdrop-blur-sm">
                <div className="flex items-center gap-2">
                  <p className="min-w-0 flex-1 truncate font-mono text-[11px] text-muted-foreground">
                    {picked
                      ? `${picked.tag}${picked.sectionId ? " · " + picked.sectionId : ""} · ${picked.text || "no text"}`
                      : "Click an element in the preview"}
                  </p>
                </div>
                <form
                  className="mt-2 flex items-center gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void applyEdit();
                  }}
                >
                  <Input
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                    disabled={!picked || busy}
                    placeholder={
                      picked
                        ? "What should change?"
                        : "Select something first"
                    }
                    aria-label="Edit instruction"
                    className="h-8"
                  />
                  <Button type="submit" size="sm" disabled={!canApply}>
                    {busy ? <Loader2 className="size-3.5 animate-spin" /> : null}
                    Apply
                  </Button>
                </form>
                {error ? (
                  <p className="mt-2 text-xs text-destructive">{error}</p>
                ) : null}
              </div>
            )}
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

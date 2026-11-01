"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  Check,
  ChevronRight,
  Clock,
  Code2,
  ExternalLink,
  FilePlus2,
  History,
  LayoutTemplate,
  Lightbulb,
  Loader2,
  Palette,
  RotateCcw,
  Sparkles,
  Type,
  Wand2,
  Wrench,
  X,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import {
  getStudioCheckpoints,
  getStudioSuggestions,
  studioRestore,
  studioTurn,
  studioUndo,
  type StudioCheckpoint,
  type StudioIdeas,
  type StudioEvent,
  type StudioSuggestion,
} from "@/lib/api";
import { SparrowMark } from "@/components/sparrow-mark";
import { pageName, type PickedElement } from "@/components/preview-pane";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

/**
 * The studio: where the owner keeps changing a finished site.
 *
 * The owner is not an engineer, so the panel leads with what it can DO — a
 * grid of the kinds of change it makes, and ideas written by the backend for
 * THIS site — rather than an empty box. A tap never runs anything on its own:
 * an idea opens as an editable card, a capability starts a sentence in the
 * composer, because a change the owner did not mean is worse than one more
 * click. While the agent works its activity streams the way a coding agent's
 * terminal does, then folds away under a reply that links to the page that
 * changed. Every version is kept; the history view goes back to any of them.
 */

type Todo = { content: string; status: "pending" | "in_progress" | "completed" };

// One line of the activity log. Tool lines gain their result when it arrives;
// phases are the workshop's own steps (build, look, polish) between them.
type Entry =
  | { type: "phase"; text: string }
  | { type: "note"; text: string }
  | {
      type: "tool";
      id: string;
      tool: string;
      target: string;
      detail: string;
      result?: { ok: boolean; summary: string };
    };

type Turn = {
  message: string;
  log: Entry[];
  todos: Todo[];
  state: "running" | "done" | "reverted" | "error";
  startedAt: number;
  seconds?: number;
  reply?: string;
  checkpoint?: string | null;
  changed?: string[];
  attached?: PickedElement[];
};

const TOOL_LABEL: Record<string, string> = {
  read: "Read",
  write: "Write",
  edit: "Edit",
  bash: "Bash",
  glob: "Glob",
  grep: "Grep",
  read_image: "View",
  subagent: "Task",
  skill: "Skill",
  mcp__studio__generate_asset: "Generate",
};

function phaseText(text: string): string {
  if (text === "starting") return "Starting up";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// Fold one streamed event into the turn it belongs to.
function apply(t: Turn, e: StudioEvent): Turn {
  switch (e.kind) {
    case "status":
      return { ...t, log: [...t.log, { type: "phase", text: phaseText(e.text) }] };
    case "note":
      return { ...t, log: [...t.log, { type: "note", text: e.text }] };
    case "tool":
      return {
        ...t,
        log: [...t.log, { type: "tool", id: e.id, tool: e.tool, target: e.target, detail: e.detail }],
      };
    case "tool_result":
      return {
        ...t,
        log: t.log.map((x) =>
          x.type === "tool" && x.id === e.id ? { ...x, result: { ok: e.ok, summary: e.summary } } : x
        ),
      };
    case "todos":
      return { ...t, todos: e.items };
    default:
      return t;
  }
}

function ActivityLog({ turn, now }: { turn: Turn; now: number }) {
  const running = turn.state === "running";
  const [open, setOpen] = useState(true);
  // Fold away once the change has landed; the reply is what matters then.
  useEffect(() => {
    if (!running) setOpen(false);
  }, [running]);
  const steps = turn.log.filter((x) => x.type === "tool").length;
  const secs = running ? Math.max(0, Math.round((now - turn.startedAt) / 1000)) : turn.seconds;
  if (!turn.log.length && !turn.todos.length && !running) return null;

  return (
    <div className="mb-2 overflow-hidden rounded-lg border border-border bg-black/30">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[11px] text-muted-foreground hover:text-foreground"
      >
        {running ? (
          <Loader2 className="size-3 animate-spin" />
        ) : (
          <ChevronRight className={cn("size-3 transition-transform", open && "rotate-90")} />
        )}
        <span>
          {running ? "Working" : "Activity"} · {steps} step{steps === 1 ? "" : "s"}
          {secs !== undefined ? ` · ${secs}s` : ""}
        </span>
      </button>

      {open && (
        <div className="max-h-80 overflow-y-auto border-t border-border px-3 py-2 font-mono text-[11px] leading-[1.55]">
          {turn.todos.length > 0 && (
            <div className="mb-2 rounded-md border border-border/60 bg-card/40 px-2.5 py-1.5">
              {turn.todos.map((td, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex gap-1.5",
                    td.status === "completed" && "text-muted-foreground line-through",
                    td.status === "in_progress" && "text-foreground",
                    td.status === "pending" && "text-muted-foreground"
                  )}
                >
                  <span>{td.status === "completed" ? "☒" : td.status === "in_progress" ? "◐" : "☐"}</span>
                  <span className="whitespace-normal">{td.content}</span>
                </div>
              ))}
            </div>
          )}

          {turn.log.map((x, i) => {
            if (x.type === "phase") {
              return (
                <div key={i} className="my-1 flex items-center gap-2 text-muted-foreground">
                  <span className="h-px flex-1 bg-border" />
                  <span className="font-sans text-[10.5px] uppercase tracking-wide">{x.text}</span>
                  <span className="h-px flex-1 bg-border" />
                </div>
              );
            }
            if (x.type === "note") {
              return (
                <div key={i} className="my-1 flex gap-1.5 font-sans text-xs text-foreground/90">
                  <span className="text-primary">✻</span>
                  <span>{x.text}</span>
                </div>
              );
            }
            const pending = !x.result;
            return (
              <div key={i} className="mb-1">
                <div className="flex min-w-0 items-baseline gap-1.5">
                  <span
                    className={cn(
                      "shrink-0",
                      pending
                        ? running
                          ? "animate-pulse text-foreground/60"
                          : "text-muted-foreground"
                        : x.result!.ok
                          ? "text-emerald-400"
                          : "text-red-400"
                    )}
                  >
                    ●
                  </span>
                  <span className="shrink-0 font-semibold text-foreground">
                    {TOOL_LABEL[x.tool] ?? x.tool}
                  </span>
                  <span className="truncate text-foreground/80" title={x.target}>
                    {x.target}
                  </span>
                  {x.detail && <span className="shrink-0 text-muted-foreground">{x.detail}</span>}
                </div>
                {x.result && (
                  <div
                    className={cn(
                      "ml-3 flex gap-1.5 whitespace-pre-wrap break-words",
                      x.result.ok ? "text-muted-foreground" : "text-red-400/90"
                    )}
                  >
                    <span className="shrink-0">⎿</span>
                    <span>{x.result.summary}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const KIND_ICON: Record<StudioSuggestion["kind"], LucideIcon> = {
  page: FilePlus2,
  content: Type,
  look: Palette,
  motion: Wand2,
  fix: Wrench,
};

// What the studio can do, as starting points. Each one begins a sentence in
// the composer for the owner to finish — the request stays theirs.
const CAPABILITIES: { icon: LucideIcon; label: string; hint: string; starter: string }[] = [
  { icon: FilePlus2, label: "Add a page", hint: "Pricing, about, careers…", starter: "Add a new page for " },
  { icon: Type, label: "Edit text", hint: "Headlines, sections, buttons", starter: "Change the text " },
  { icon: Palette, label: "Change the look", hint: "Colours, spacing, layout", starter: "Change the look of " },
  { icon: LayoutTemplate, label: "Add a section", hint: "FAQ, comparison, steps", starter: "Add a section to the home page that " },
  { icon: Wand2, label: "Add motion", hint: "Animation, interaction", starter: "Add an animation to " },
  { icon: Wrench, label: "Fix something", hint: "Anything that looks off", starter: "Fix " },
];

// A changed file → the page an owner would look at to see it.
function pageOf(file: string): { path: string; label: string } {
  const page = file.match(/^src\/app\/(?:(.+)\/)?page\.\w+$/);
  if (page) {
    const seg = (page[1] ?? "").split("/").filter((p) => !p.startsWith("(")).join("/");
    const path = seg ? `/${seg}/` : "/";
    return { path, label: `${pageName(path)} page` };
  }
  const section = file.match(/sections\/([A-Za-z0-9]+)\.\w+$/);
  if (section) {
    const name = section[1].replace(/([a-z])([A-Z])/g, "$1 $2");
    return { path: "/", label: name === "Nav" ? "Navigation" : name };
  }
  return { path: "/", label: "Site styles" };
}

function changedPlaces(files: string[] = []): { path: string; label: string }[] {
  const seen = new Set<string>();
  return files
    .filter((f) => !f.endsWith(".md"))
    .map(pageOf)
    .filter((p) => (seen.has(p.label) ? false : (seen.add(p.label), true)));
}

// What the agent receives for the elements the owner clicked: enough to know
// exactly what "this" means, and to find it in the source by its text.
function attachmentContext(items: PickedElement[]): string {
  if (!items.length) return "";
  const rows = items.map((el, i) => {
    const what = el.text ? `a <${el.tag}> reading "${el.text.slice(0, 200)}"` : `a <${el.tag}>`;
    return `${i + 1}. On the ${pageName(el.page)} page (${el.page}), ${what} — in ${el.block}.\n   Markup: ${el.html}`;
  });
  return (
    "\n\n---\nThe owner selected these elements in the preview. \"This\", \"here\" and \"it\" " +
    "refer to them. Find each in the source by its text or markup before changing it.\n" +
    rows.join("\n")
  );
}

function ElementChip({ el, onRemove }: { el: PickedElement; onRemove?: () => void }) {
  return (
    <span
      title={`${pageName(el.page)} page · ${el.block}`}
      className="flex max-w-full items-center gap-1.5 rounded-md border border-indigo-400/40 bg-indigo-500/10 py-0.5 pl-1.5 pr-1 text-[11px] text-indigo-100"
    >
      <Code2 className="size-3 shrink-0 text-indigo-300" />
      <span className="truncate">{el.label}</span>
      <span className="shrink-0 text-indigo-300/70">{pageName(el.page)}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove"
          className="shrink-0 rounded p-0.5 text-indigo-300/80 hover:bg-indigo-500/20 hover:text-white"
        >
          <X className="size-3" />
        </button>
      )}
    </span>
  );
}

function ago(at: number): string {
  const s = Math.max(0, Math.round(Date.now() / 1000 - at));
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

function HistoryView({
  projectId,
  onRestored,
  onClose,
}: {
  projectId: string;
  onRestored: () => void;
  onClose: () => void;
}) {
  const [rows, setRows] = useState<StudioCheckpoint[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    getStudioCheckpoints(projectId)
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }
  useEffect(load, [projectId]);

  async function restore(id: string) {
    setBusy(id);
    setError(null);
    try {
      await studioRestore(projectId, id);
      onRestored();
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">Version history</p>
          <p className="text-xs text-muted-foreground">Every change is kept. Going back is a change too.</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close history">
          <X className="size-4" />
        </Button>
      </div>
      {error && <p className="mb-2 text-xs text-amber-400">{error}</p>}
      {!rows && !error && (
        <div className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}
      {rows && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">No changes yet — the first one will appear here.</p>
      )}
      <ol className="relative flex flex-col gap-2 border-l border-border pl-4">
        {rows?.map((c, i) => {
          const original = c.message === "Imported the generated site";
          return (
            <li key={c.id} className="relative">
              <span
                className={cn(
                  "absolute -left-[21px] top-3 size-2.5 rounded-full border-2 border-background",
                  i === 0 ? "bg-emerald-400" : "bg-muted-foreground/50"
                )}
              />
              <div
                className={cn(
                  "rounded-lg border px-3 py-2",
                  i === 0 ? "border-emerald-500/30 bg-emerald-500/5" : "border-border bg-card/40"
                )}
              >
                <p className="line-clamp-2 text-xs text-foreground">
                  {original ? "Original generated site" : c.message}
                </p>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-[11px] text-muted-foreground">{ago(c.at)}</span>
                  {i === 0 ? (
                    <span className="text-[11px] font-medium text-emerald-400">Current</span>
                  ) : (
                    <button
                      type="button"
                      disabled={busy !== null}
                      onClick={() => restore(c.id)}
                      className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground disabled:opacity-50"
                    >
                      {busy === c.id ? <Loader2 className="size-3 animate-spin" /> : <RotateCcw className="size-3" />}
                      Go back to this
                    </button>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function StudioPanel({
  projectId,
  title,
  onSiteChanged,
  onOpenPage,
  onShowBuildLog,
  attachments = [],
  onRemoveAttachment,
  onClearAttachments,
}: {
  projectId: string;
  title: string;
  /** The site changed (a change landed, was undone or restored); reload the
   *  preview, on `path` if one is given. */
  onSiteChanged: (path?: string) => void;
  /** Show a page of the site in the preview. */
  onOpenPage: (path: string) => void;
  onShowBuildLog: () => void;
  /** Elements the owner clicked in the preview, waiting to go with the next message. */
  attachments?: PickedElement[];
  onRemoveAttachment?: (id: string) => void;
  onClearAttachments?: () => void;
}) {
  const [suggestions, setSuggestions] = useState<StudioSuggestion[] | null>(null);
  const [complete, setComplete] = useState<StudioIdeas["complete"]>(null);
  const [brokenLinks, setBrokenLinks] = useState(0);
  const [suggestError, setSuggestError] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  // A tapped idea, shown as a card to confirm before anything runs.
  const [planned, setPlanned] = useState<StudioSuggestion | null>(null);
  const [undoing, setUndoing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // Drives the running timer in the activity header.
  const [now, setNow] = useState(() => Date.now());

  const busy = turns.some((t) => t.state === "running") || undoing;

  function loadSuggestions() {
    setSuggestError(false);
    getStudioSuggestions(projectId)
      .then((ideas) => {
        setSuggestions(ideas.suggestions);
        setComplete(ideas.complete);
        setBrokenLinks(ideas.broken_links ?? 0);
      })
      .catch(() => setSuggestError(true));
  }

  useEffect(() => {
    loadSuggestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  // A freshly picked element means the owner is about to say something about
  // it: put the cursor where they will type.
  useEffect(() => {
    if (attachments.length) {
      setPlanned(null);
      setShowHistory(false);
      inputRef.current?.focus();
    }
  }, [attachments.length]);

  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [busy]);

  function patchLast(fn: (t: Turn) => Turn) {
    setTurns((prev) => (prev.length ? [...prev.slice(0, -1), fn(prev[prev.length - 1])] : prev));
  }

  function start(starter: string) {
    setPlanned(null);
    setDraft(starter);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(starter.length, starter.length);
    });
  }

  async function send(message: string) {
    const text = message.trim();
    if (!text || busy) return;
    const attached = attachments;
    setDraft("");
    setPlanned(null);
    setShowHistory(false);
    onClearAttachments?.();
    setTurns((prev) => [
      ...prev,
      { message: text, attached, log: [], todos: [], state: "running", startedAt: Date.now() },
    ]);
    let ended = false;
    try {
      await studioTurn(projectId, text + attachmentContext(attached), (e) => {
        if (e.kind === "done") {
          ended = true;
          patchLast((t) => ({
            ...t,
            state: e.reverted ? "reverted" : "done",
            reply: e.reply,
            checkpoint: e.checkpoint,
            changed: e.changed,
            seconds: Math.round(e.seconds),
          }));
          // Show the change where it happened, not wherever the preview was.
          if (e.checkpoint) onSiteChanged(changedPlaces(e.changed)[0]?.path);
          else if (e.reverted) onSiteChanged();
          if (e.checkpoint) {
            setSuggestions(null);
            setComplete(null);
            loadSuggestions();
          }
          return;
        }
        if (e.kind === "error") {
          ended = true;
          patchLast((t) => ({ ...t, state: "error", reply: e.text }));
          return;
        }
        patchLast((t) => apply(t, e));
      });
      if (!ended) {
        patchLast((t) => ({
          ...t,
          state: "error",
          reply: "The connection closed before the change finished. It may still land — check the history.",
        }));
      }
    } catch (err) {
      patchLast((t) => ({
        ...t,
        state: "error",
        reply: err instanceof Error ? err.message : String(err),
      }));
    }
  }

  async function undo() {
    setUndoing(true);
    try {
      await studioUndo(projectId);
      setTurns((prev) => [
        ...prev,
        {
          message: "Undo",
          log: [],
          todos: [],
          state: "done",
          startedAt: Date.now(),
          reply: "Put the site back the way it was before the last change.",
        },
      ]);
      onSiteChanged();
      setSuggestions(null);
      loadSuggestions();
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        {
          message: "Undo",
          log: [],
          todos: [],
          state: "error",
          startedAt: Date.now(),
          reply: err instanceof Error ? err.message : String(err),
        },
      ]);
    } finally {
      setUndoing(false);
    }
  }

  const lastKept = [...turns].reverse().find((t) => t.state === "done" && t.checkpoint);
  const fresh = turns.length === 0;

  const completeCard = complete && !planned && (
    <button
      type="button"
      disabled={busy}
      onClick={() => {
        setPlanned({ label: complete.label, prompt: complete.prompt, kind: "page" });
        setDraft(complete.prompt);
      }}
      className="group mb-4 w-full rounded-xl bg-gradient-to-br from-indigo-500/70 via-fuchsia-500/50 to-amber-400/60 p-px text-left disabled:opacity-50"
    >
      <div className="rounded-[11px] bg-card/95 p-3.5 transition-colors group-hover:bg-card/80">
        <div className="mb-1 flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-fuchsia-500 text-white">
            <Sparkles className="size-3.5" />
          </span>
          <span className="text-sm font-semibold text-foreground">Complete the site</span>
          <span className="ml-auto rounded-full bg-indigo-500/15 px-2 py-0.5 text-[10.5px] font-medium text-indigo-200">
            Recommended
          </span>
        </div>
        <p className="mb-2 text-xs text-muted-foreground">
          Every page this site should have, built in its design, linked from the nav and footer
          {brokenLinks > 0 ? ` — and the ${brokenLinks} link${brokenLinks === 1 ? "" : "s"} that go nowhere today fixed` : ""}.
        </p>
        <p className="line-clamp-2 text-[11.5px] text-foreground/70">{complete.prompt}</p>
      </div>
    </button>
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <SparrowMark className="size-4 shrink-0" />
          <span className="truncate text-sm font-medium text-foreground">{title}</span>
          <span className="flex shrink-0 items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10.5px] font-medium text-emerald-400">
            <span className="size-1.5 rounded-full bg-emerald-400" /> Studio
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowHistory((h) => !h)}
            className={cn("text-xs", showHistory && "bg-muted")}
          >
            <History className="size-3.5" /> History
          </Button>
          <Button variant="ghost" size="sm" onClick={onShowBuildLog} className="text-xs">
            Build log
          </Button>
        </div>
      </div>

      {showHistory ? (
        <HistoryView
          projectId={projectId}
          onClose={() => setShowHistory(false)}
          onRestored={() => {
            onSiteChanged();
            setSuggestions(null);
            loadSuggestions();
          }}
        />
      ) : (
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
          {fresh && (
            <div className="mb-5">
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                What should we change?
              </h2>
              <p className="mb-4 text-sm text-muted-foreground">
                Ask for anything on the site. Each change is built, checked on the page, and can be
                undone.
              </p>
              {completeCard}
              <div className="grid grid-cols-2 gap-2">
                {CAPABILITIES.map(({ icon: Icon, label, hint, starter }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => start(starter)}
                    className="group rounded-xl border border-border bg-card/50 p-3 text-left transition-colors hover:border-primary/50 hover:bg-card"
                  >
                    <Icon className="mb-2 size-4 text-muted-foreground transition-colors group-hover:text-primary" />
                    <p className="text-[13px] font-medium text-foreground">{label}</p>
                    <p className="text-[11px] text-muted-foreground">{hint}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((t, i) => {
            const places = changedPlaces(t.changed);
            const isLastKept = t === lastKept;
            return (
              <div key={i} className="mb-5">
                <div className="mb-2 ml-8 rounded-2xl rounded-tr-sm bg-secondary/70 px-3.5 py-2.5 text-sm text-foreground">
                  {t.attached && t.attached.length > 0 && (
                    <div className="mb-1.5 flex flex-wrap gap-1">
                      {t.attached.map((el) => (
                        <ElementChip key={el.id} el={el} />
                      ))}
                    </div>
                  )}
                  {t.message}
                </div>
                <ActivityLog turn={t} now={now} />
                {t.reply && (
                  <div
                    className={cn(
                      "rounded-xl border px-3.5 py-3 text-sm",
                      t.state === "error" || t.state === "reverted"
                        ? "border-amber-500/40 bg-amber-500/10"
                        : "border-border bg-card/60"
                    )}
                  >
                    <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium">
                      {t.state === "done" && t.checkpoint ? (
                        <>
                          <Check className="size-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Changed</span>
                          {t.seconds !== undefined && (
                            <span className="font-normal text-muted-foreground">· {t.seconds}s</span>
                          )}
                        </>
                      ) : t.state === "done" ? (
                        <span className="text-muted-foreground">No change needed</span>
                      ) : t.state === "reverted" ? (
                        <>
                          <AlertTriangle className="size-3.5 text-amber-400" />
                          <span>That change broke the site, so nothing was kept</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="size-3.5 text-amber-400" />
                          <span>Something went wrong</span>
                        </>
                      )}
                    </div>
                    <p className="whitespace-pre-line text-foreground">{t.reply.replace(/`/g, "")}</p>
                    {(places.length > 0 || isLastKept) && (
                      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                        {places.map((p) => (
                          <button
                            key={p.label}
                            type="button"
                            onClick={() => onOpenPage(p.path)}
                            className="flex items-center gap-1 rounded-full border border-border bg-background/40 px-2.5 py-0.5 text-[11px] text-foreground hover:border-primary/50"
                          >
                            <ExternalLink className="size-3" /> {p.label}
                          </button>
                        ))}
                        {isLastKept && !busy && (
                          <button
                            type="button"
                            onClick={undo}
                            className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                          >
                            <RotateCcw className="size-3" /> Undo
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {planned && (
            <div className="mb-4 rounded-xl border border-primary/40 bg-primary/5 p-3.5">
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Lightbulb className="size-3.5 text-primary" /> {planned.label} · here is what I&apos;ll do
              </p>
              <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={5}
                className="mb-3 rounded-lg border border-border bg-background/40 p-2 text-sm"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={() => send(draft)} disabled={busy || !draft.trim()}>
                  <Sparkles className="size-3" /> Do it
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setPlanned(null);
                    setDraft("");
                  }}
                >
                  Not now
                </Button>
              </div>
            </div>
          )}

          {!planned && (
            <div>
              {!fresh && completeCard}
              <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Lightbulb className="size-3.5" /> Ideas for {title}
              </p>
              {suggestions === null && !suggestError && (
                <div className="flex flex-col gap-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-16 animate-pulse rounded-xl bg-muted" />
                  ))}
                </div>
              )}
              {suggestError && (
                <button type="button" onClick={loadSuggestions} className="text-xs text-muted-foreground underline">
                  Couldn&apos;t load ideas — retry
                </button>
              )}
              {suggestions && (
                <div className="flex flex-col gap-2">
                  {suggestions.map((s) => {
                    const Icon = KIND_ICON[s.kind] ?? Lightbulb;
                    return (
                      <button
                        key={s.label}
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setPlanned(s);
                          setDraft(s.prompt);
                        }}
                        className="group flex gap-3 rounded-xl border border-border bg-card/40 p-3 text-left transition-colors hover:border-primary/50 hover:bg-card disabled:opacity-50"
                      >
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground group-hover:text-primary">
                          <Icon className="size-3.5" />
                        </span>
                        <span className="min-w-0">
                          <span className="block text-[13px] font-medium text-foreground">{s.label}</span>
                          <span className="line-clamp-2 text-[11.5px] text-muted-foreground">{s.prompt}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <form
        className="border-t border-border p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        {!fresh && !planned && (
          <div className="mb-2 flex gap-1 overflow-x-auto">
            {CAPABILITIES.map(({ icon: Icon, label, starter }) => (
              <button
                key={label}
                type="button"
                disabled={busy}
                onClick={() => start(starter)}
                className="flex shrink-0 items-center gap-1 rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground hover:border-primary/50 hover:text-foreground disabled:opacity-50"
              >
                <Icon className="size-3" /> {label}
              </button>
            ))}
          </div>
        )}
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {attachments.map((el) => (
              <ElementChip key={el.id} el={el} onRemove={() => onRemoveAttachment?.(el.id)} />
            ))}
          </div>
        )}
        <div className="flex items-end gap-2 rounded-xl border border-border bg-card/60 px-3 py-2 focus-within:border-primary/50">
          <Textarea
            ref={inputRef}
            value={planned ? "" : draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(draft);
              }
            }}
            rows={2}
            placeholder={
              busy
                ? "Working on it…"
                : planned
                  ? "Confirm the idea above, or type your own"
                  : attachments.length
                    ? "What should change about the selected element?"
                    : "Describe a change… or use Select to point at something"
            }
            disabled={busy || Boolean(planned)}
            className="text-sm"
          />
          <Button type="submit" size="icon" disabled={busy || !draft.trim() || Boolean(planned)} aria-label="Send">
            {busy ? <Loader2 className="size-3.5 animate-spin" /> : <ArrowUp className="size-3.5" />}
          </Button>
        </div>
        <p className="mt-1.5 flex items-center gap-1 text-[11px] text-muted-foreground">
          <Clock className="size-3" /> Usually 1–3 minutes · Enter to send · every change can be undone
        </p>
      </form>
    </div>
  );
}

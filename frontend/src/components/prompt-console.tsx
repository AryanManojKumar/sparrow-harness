"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, Loader2, Mic } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  hasPlaceholder,
  nextPlaceholder,
  suggest,
  type Suggestion,
} from "@/lib/suggest";
import { slugify } from "@/lib/api";
import { extractUrls, isHttpUrl } from "@/lib/urls";
import { SparrowMark } from "@/components/sparrow-mark";
import { ReferenceSiteRow } from "@/components/reference-site-row";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

// The scout stage needs at least two readable reference sites to rank
// against (backend/src/sparrow/steps.py: step_sources) — there is no way to
// run for real with fewer. Prefilled with two sites confirmed to extract
// cleanly through Playwright — stripe.com was tried first and hung
// indefinitely under scout.extract(), almost certainly its bot detection;
// these two are what backend/API.md's own example uses.
const DEFAULT_URLS = ["https://linear.app", "https://kiro.dev"];

const MIN_CHARS = 8;
// Long enough to clear a normal pause between words/sentences while typing,
// so a completion fires once per thought instead of once per pause — each
// call is a real LLM request (~$, ~5-6s), not worth spending on a half-typed
// idea that's about to change anyway.
const DEBOUNCE_MS = 900;

export function PromptConsole() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [hasTyped, setHasTyped] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [hint, setHint] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isDebouncing, setIsDebouncing] = useState(false);
  const [urls, setUrls] = useState<string[]>(DEFAULT_URLS);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Set right before a suggestion writes `value` programmatically, so the
  // effect below skips the /suggest call that text change would otherwise
  // trigger — the text just came from the API, asking it again is wasted.
  const skipFetchRef = useRef(false);
  // URLs the user explicitly removed. Without this, a URL still sitting in
  // the prompt text gets re-added by the extractor on the very next
  // keystroke, so the remove button appears not to work.
  const dismissedRef = useRef<Set<string>>(new Set());
  // Selection to apply once React has committed a programmatic setValue —
  // setSelectionRange against the pre-update DOM would land on stale text.
  const pendingSelectRef = useRef<[number, number] | null>(null);

  useEffect(() => {
    abortRef.current?.abort();

    if (skipFetchRef.current) {
      skipFetchRef.current = false;
      setSuggestions([]);
      setActiveIndex(-1);
      setIsDebouncing(false);
      return;
    }

    if (value.trim().length < MIN_CHARS) {
      setSuggestions([]);
      setHint(null);
      setActiveIndex(-1);
      setIsSuggesting(false);
      setIsDebouncing(false);
      return;
    }

    // Pending the moment a keystroke qualifies, not just once the request is
    // in flight — Send gates on this too, so it can't fire mid-debounce and
    // beat the completion that was supposedly about to load.
    setIsDebouncing(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const timer = setTimeout(() => {
      setIsDebouncing(false);
      setIsSuggesting(true);
      suggest(value, controller.signal)
        .then((res) => {
          setSuggestions(res.suggestions);
          setHint(res.suggestions.length > 0 ? res.hint : null);
          setActiveIndex(-1);
        })
        .catch(() => {
          // Aborted by a newer keystroke, or the request failed — either way
          // autocomplete is an accelerator, not a step. Fail silently.
        })
        .finally(() => setIsSuggesting(false));
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  // Applies a selection queued by acceptSuggestion / Tab, once the new value
  // is actually in the DOM.
  useEffect(() => {
    const sel = pendingSelectRef.current;
    if (!sel || !textareaRef.current) return;
    pendingSelectRef.current = null;
    textareaRef.current.focus();
    textareaRef.current.setSelectionRange(sel[0], sel[1]);
  }, [value]);

  /** Pull any URL in the prompt into the reference list, minus dismissed ones. */
  function absorbUrls(text: string) {
    const found = extractUrls(text).filter(
      (u) => !dismissedRef.current.has(u.toLowerCase())
    );
    if (found.length === 0) return;
    setUrls((prev) => {
      const existing = new Set(prev.map((u) => u.trim().toLowerCase()));
      const additions = found.filter((u) => !existing.has(u.toLowerCase()));
      if (additions.length === 0) return prev;
      const withoutEmpty = prev.filter((u) => u.trim() !== "");
      return [...withoutEmpty, ...additions];
    });
  }

  function handleChange(next: string) {
    setValue(next);
    if (next.length > 0 && !hasTyped) setHasTyped(true);
    absorbUrls(next);
  }

  function removeUrl(index: number) {
    setUrls((prev) => {
      const target = prev[index]?.trim().toLowerCase();
      if (target) dismissedRef.current.add(target);
      return prev.filter((_, i) => i !== index);
    });
    setUrlError(null);
  }

  function acceptSuggestion(s: Suggestion) {
    skipFetchRef.current = true;
    // Every suggestion is a complete, independent elaboration of the idea
    // (the backend always returns a full restated prompt, never a bare
    // continuation) — so accepting one replaces the draft outright. Trying
    // to detect "is this a continuation" and append was the bug: the
    // suggestion restates the opening in its own words often enough that
    // heuristic produced visible duplicates instead of catching them.
    const next = s.text.replace(/^a /i, "").replace(/^./, (c) => c.toUpperCase());
    setValue(next);
    setSuggestions([]);
    setHint(null);
    setActiveIndex(-1);
    // Suggestions arrive with `[blanks]` to fill in — put the cursor on the
    // first one so typing replaces it, instead of leaving the user to hunt
    // for the brackets themselves.
    pendingSelectRef.current = nextPlaceholder(next) ?? [next.length, next.length];
    absorbUrls(next);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Tab cycles through the remaining `[blanks]`, whether or not the
    // suggestion list is still open.
    if (e.key === "Tab" && hasPlaceholder(value)) {
      e.preventDefault();
      const from = (e.currentTarget.selectionEnd ?? 0) + 1;
      const sel = nextPlaceholder(value, from);
      if (sel) e.currentTarget.setSelectionRange(sel[0], sel[1]);
      return;
    }

    if (suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter" && !e.shiftKey && activeIndex >= 0) {
      e.preventDefault();
      acceptSuggestion(suggestions[activeIndex]);
    } else if (e.key === "Escape") {
      setSuggestions([]);
      setActiveIndex(-1);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim() || isDebouncing || isSuggesting || isStarting) return;
    // A literal "[what you sell]" reaching /interview would be written into
    // the brief verbatim, so the blanks are a hard gate, not a nudge.
    if (hasPlaceholder(value)) return;

    const cleanUrls = urls.map((u) => u.trim()).filter(Boolean);
    if (cleanUrls.length < 2 || cleanUrls.some((u) => !isHttpUrl(u))) {
      setUrlError("Two full URLs (https://…) are needed to start a real run.");
      return;
    }
    setUrlError(null);
    setIsStarting(true);

    // The actual interview + project-creation + first run leg happen on the
    // /build screen, where progress is visible — this just hands off what
    // it collected. sessionStorage rather than the query string because a
    // brief plus several reference URLs is bigger than a URL comfortably carries.
    const projectId = slugify(value.trim());
    sessionStorage.setItem(
      `sparrow:${projectId}`,
      JSON.stringify({ prompt: value.trim(), urls: cleanUrls })
    );
    router.push(`/build?id=${projectId}`);
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center">
      {/* Reserved zone above the box — fixed height so nothing below jumps
          when the sparrow leaves. */}
      <div className="mb-6 flex h-16 items-end justify-center">
        <AnimatePresence>
          {!hasTyped && (
            <motion.div
              key="sparrow"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
            >
              <SparrowMark className="size-11" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <h1 className="mb-8 text-center text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
        Start with one prompt. You can change everything later.
      </h1>

      <form onSubmit={handleSubmit} className="w-full">
        <div className="rounded-2xl border border-border bg-card/60 p-4 shadow-2xl shadow-black/40 backdrop-blur-sm">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your business and we'll bring it to life…"
            rows={3}
            className="min-h-20"
          />

          <div className="mt-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {isSuggesting && !hasPlaceholder(value) && (
                <Loader2 className="size-3 animate-spin" />
              )}
              {/* Blanks outrank the loading states: they are the one thing
                  the user has to act on before anything can start. */}
              {hasPlaceholder(value)
                ? "Fill in the [blanks] — Tab to jump between them"
                : isSuggesting
                  ? "Finding a direction…"
                  : isDebouncing
                    ? "Waiting for you to finish typing…"
                    : value.trim().length > 0
                      ? `${value.trim().length} characters`
                      : "One line is enough to start"}
            </span>
            <div className="flex items-center gap-2">
              <Button type="button" variant="ghost" size="icon" aria-label="Voice input">
                <Mic />
              </Button>
              <Button
                type="submit"
                size="icon"
                disabled={
                  !value.trim() ||
                  isDebouncing ||
                  isSuggesting ||
                  isStarting ||
                  hasPlaceholder(value)
                }
                aria-label="Start"
              >
                {isStarting ? <Loader2 className="animate-spin" /> : <ArrowUp />}
              </Button>
            </div>
          </div>
        </div>

        {/* Autocomplete rows. CSS grid-rows trick for a smooth, jump-free
            height animation without measuring anything in JS. */}
        <div
          className="grid transition-[grid-template-rows] duration-300 ease-out"
          style={{ gridTemplateRows: suggestions.length ? "1fr" : "0fr" }}
        >
          <div className="overflow-hidden">
            {/* What the brief is still missing — the backend picks the gap
                (offering / audience / specifics / purpose) these completions
                were aimed at, so the user can see why it is asking. */}
            {hint && (
              <p className="mt-3 px-3 text-xs font-medium text-muted-foreground">
                {hint}
              </p>
            )}
            <ul className="mt-2 flex flex-col gap-1">
              {suggestions.map((s, i) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => acceptSuggestion(s)}
                    onMouseEnter={() => setActiveIndex(i)}
                    className={cn(
                      "group/row flex w-full items-baseline gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                      i === activeIndex ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/60"
                    )}
                  >
                    {/* Truncated by default; hovering the row reveals the
                        full candidate instead of leaving it cut off. */}
                    <span className="overflow-hidden text-ellipsis whitespace-nowrap text-foreground group-hover/row:overflow-visible group-hover/row:text-clip group-hover/row:whitespace-normal">
                      {s.text}
                    </span>
                    <span className="ml-auto shrink-0 self-start text-xs text-muted-foreground">
                      {s.category}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Scout needs two readable reference sites to rank against — skeleton,
            rhythm, section order (CLAUDE.md §5). Any URL typed into the prompt
            above lands here automatically; removing one keeps it removed. */}
        <div className="mt-3 rounded-xl border border-border bg-card/40 p-3">
          <p className="mb-2 text-xs font-medium text-muted-foreground">
            Reference sites — two needed to design against
          </p>
          <div className="flex flex-col gap-2">
            {urls.map((u, i) => (
              <ReferenceSiteRow
                key={i}
                value={u}
                onChange={(next) => {
                  const nextUrls = [...urls];
                  nextUrls[i] = next;
                  setUrls(nextUrls);
                  setUrlError(null);
                }}
                onRemove={() => removeUrl(i)}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={() => setUrls((prev) => [...prev, ""])}
            className="mt-2 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            + Add another site
          </button>
          {urlError && <p className="mt-2 text-xs text-destructive">{urlError}</p>}
        </div>
      </form>
    </div>
  );
}

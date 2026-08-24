"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, Loader2, Mic } from "lucide-react";

import { cn } from "@/lib/utils";
import { suggest, type Suggestion } from "@/lib/suggest";
import { sourceFor, type Source } from "@/lib/sources";
import { SparrowMark } from "@/components/sparrow-mark";
import { SourceCard } from "@/components/source-card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

const MIN_CHARS = 8;
const DEBOUNCE_MS = 350;
const ATTACH_MS = 550;

export function PromptConsole() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [hasTyped, setHasTyped] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const [isAttaching, setIsAttaching] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const attachTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Set right before a suggestion writes `value` programmatically, so the
  // effect below skips the /suggest call that text change would otherwise
  // trigger — the text just came from the API, asking it again is wasted.
  const skipFetchRef = useRef(false);

  useEffect(() => {
    abortRef.current?.abort();

    if (skipFetchRef.current) {
      skipFetchRef.current = false;
      setSuggestions([]);
      setActiveIndex(-1);
      return;
    }

    if (value.trim().length < MIN_CHARS) {
      setSuggestions([]);
      setActiveIndex(-1);
      setIsSuggesting(false);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    const timer = setTimeout(() => {
      setIsSuggesting(true);
      suggest(value, controller.signal)
        .then((results) => {
          setSuggestions(results);
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

  function handleChange(next: string) {
    setValue(next);
    if (next.length > 0 && !hasTyped) setHasTyped(true);

    // A manual edit means the text no longer matches what the attached
    // reference was picked for — drop it rather than show a stale citation.
    if (source || isAttaching) {
      if (attachTimerRef.current) clearTimeout(attachTimerRef.current);
      setIsAttaching(false);
      setSource(null);
    }
  }

  function acceptSuggestion(s: Suggestion) {
    skipFetchRef.current = true;
    setValue((prev) => {
      const trimmed = prev.trim();
      // The suggestion already restates the query as its own prefix (the
      // backend elaborates on what was typed, it doesn't hand back a bare
      // continuation) — appending would duplicate it. Replace whenever the
      // suggestion already contains what's typed so far; only append for
      // the case where it's a genuine continuation.
      const startsSame = trimmed.length > 0 && s.text.toLowerCase().startsWith(trimmed.toLowerCase());
      if (startsSame || trimmed.length === 0) {
        return s.text.replace(/^a /, "").replace(/^./, (c) => c.toUpperCase());
      }
      return /\b(a|an|the)\s*$/i.test(trimmed) ? s.text : `${trimmed} ${s.text}`;
    });
    setSuggestions([]);
    setActiveIndex(-1);
    textareaRef.current?.focus();

    // Attaching the reference is treated as its own brief load — Send stays
    // disabled until it resolves, same as waiting on any other attachment.
    if (attachTimerRef.current) clearTimeout(attachTimerRef.current);
    setSource(null);
    setIsAttaching(true);
    const picked = sourceFor(s);
    attachTimerRef.current = setTimeout(() => {
      setSource(picked);
      setIsAttaching(false);
    }, ATTACH_MS);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
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
    if (!value.trim() || isAttaching) return;
    // Navigates in-app to the workspace — never off to an external host.
    // Once POST /runs exists this becomes a real run id instead of the raw
    // prompt in the query string.
    const params = new URLSearchParams({ p: value.trim() });
    if (source) params.set("source", JSON.stringify(source));
    router.push(`/build?${params.toString()}`);
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
              {isSuggesting && <Loader2 className="size-3 animate-spin" />}
              {isSuggesting
                ? "Finding a direction…"
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
                disabled={!value.trim() || isAttaching}
                aria-label="Start"
              >
                <ArrowUp />
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
            <ul className="mt-3 flex flex-col gap-1">
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

        {/* The reference an accepted suggestion drew from — attaches after a
            short beat (mocked here; a real lookup later), and is what Send
            waits on. */}
        {(source || isAttaching) && (
          <div className="mt-3">
            {isAttaching ? (
              <div className="flex items-center gap-2 rounded-xl border border-dashed border-border px-3 py-2.5 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                Attaching reference…
              </div>
            ) : (
              source && <SourceCard source={source} onRemove={() => setSource(null)} />
            )}
          </div>
        )}
      </form>
    </div>
  );
}

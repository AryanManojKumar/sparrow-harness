"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, Mic } from "lucide-react";

import { cn } from "@/lib/utils";
import { suggest, type Suggestion } from "@/lib/suggest";
import { SparrowMark } from "@/components/sparrow-mark";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

const MIN_CHARS = 8;
const DEBOUNCE_MS = 350;

export function PromptConsole() {
  const [value, setValue] = useState("");
  const [hasTyped, setHasTyped] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    abortRef.current?.abort();

    if (value.trim().length < MIN_CHARS) {
      setSuggestions([]);
      setActiveIndex(-1);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    const timer = setTimeout(() => {
      suggest(value, controller.signal)
        .then((results) => {
          setSuggestions(results);
          setActiveIndex(-1);
        })
        .catch(() => {
          // Aborted by a newer keystroke, or the request failed — either way
          // autocomplete is an accelerator, not a step. Fail silently.
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  function handleChange(next: string) {
    setValue(next);
    if (next.length > 0 && !hasTyped) setHasTyped(true);
  }

  function acceptSuggestion(s: Suggestion) {
    setValue((prev) => {
      const trimmed = prev.trim();
      // If the current text already reads like the start of a sentence,
      // complete it; otherwise just drop the candidate in whole.
      return /\b(a|an|the)\s*$/i.test(trimmed) || trimmed.length === 0
        ? s.text.replace(/^a /, "").replace(/^./, (c) => c.toUpperCase())
        : `${trimmed} ${s.text}`;
    });
    setSuggestions([]);
    setActiveIndex(-1);
    textareaRef.current?.focus();
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
    if (!value.trim()) return;
    // Wired to POST /runs once the backend exists — see backend/README.md.
    // For now the console is UI-only.
    console.log("[sparrow] would start a run with:", value);
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
            <span className="text-xs text-muted-foreground">
              {value.trim().length > 0 ? `${value.trim().length} characters` : "One line is enough to start"}
            </span>
            <div className="flex items-center gap-2">
              <Button type="button" variant="ghost" size="icon" aria-label="Voice input">
                <Mic />
              </Button>
              <Button
                type="submit"
                size="icon"
                disabled={!value.trim()}
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
                      "flex w-full items-baseline gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                      i === activeIndex ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/60"
                    )}
                  >
                    <span className="truncate text-foreground">{s.text}</span>
                    <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                      {s.category}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </form>
    </div>
  );
}

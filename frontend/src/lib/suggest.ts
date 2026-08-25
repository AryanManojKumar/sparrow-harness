/**
 * Suggestion source for the prompt box's autocomplete rows.
 *
 * Backed by the real POST /suggest (Interviewer.suggest, Tier.CHEAP — see
 * backend/src/sparrow/agents/interviewer.py). That route never raises; it
 * returns an empty list on any failure so a broken completion can't
 * interrupt typing, which is why this wrapper doesn't need its own retry
 * logic — just pass the failure through and let the caller no-op it.
 *
 * Completions aim at what is still UNKNOWN about the business rather than at
 * a page shape, so each one carries `[bracketed]` blanks for the user to
 * fill in, and the response says which dimension of the brief it was
 * probing. The UI has to surface that: an unfilled blank sent through to
 * /interview would put the literal text "[what you sell]" into the brief.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Suggestion = {
  id: string;
  /** The completed prompt text, shown as the row's main line. */
  text: string;
  /** What category this expands into, shown as a small trailing hint. */
  category: string;
};

export type SuggestResponse = {
  /** Which part of the brief these completions probed: offering | audience | specifics | purpose. */
  gap: string | null;
  /** Human-readable version of the gap, e.g. "Say what you make and who buys". */
  hint: string | null;
  suggestions: Suggestion[];
};

const EMPTY: SuggestResponse = { gap: null, hint: null, suggestions: [] };

/**
 * Returns up to `limit` candidates for the given partial prompt, plus which
 * gap in the brief they were aimed at. Rejects with an AbortError if
 * `signal` fires first — callers cancel on every new keystroke since the
 * backend call takes several seconds.
 */
export async function suggest(
  query: string,
  signal?: AbortSignal,
  limit = 5
): Promise<SuggestResponse> {
  const res = await fetch(`${API_URL}/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ q: query, limit }),
    signal,
  });

  if (!res.ok) return EMPTY;

  const data: Partial<SuggestResponse> = await res.json();
  return {
    gap: data.gap ?? null,
    hint: data.hint ?? null,
    suggestions: data.suggestions ?? [],
  };
}

/* ------------------------------------------------------------------ blanks */

const PLACEHOLDER = /\[[^\]\n]+\]/g;

/** True while the draft still has a `[blank]` the user hasn't replaced. */
export function hasPlaceholder(text: string): boolean {
  return new RegExp(PLACEHOLDER.source).test(text);
}

/**
 * Range of the next `[blank]` at or after `from`, wrapping to the start if
 * there is none later. Returned as a selection range so the caller can put
 * the cursor on it and let the user type straight over it.
 */
export function nextPlaceholder(text: string, from = 0): [number, number] | null {
  const re = new RegExp(PLACEHOLDER.source, "g");
  re.lastIndex = from;
  let m = re.exec(text);
  if (!m) {
    re.lastIndex = 0;
    m = re.exec(text);
  }
  return m ? [m.index, m.index + m[0].length] : null;
}

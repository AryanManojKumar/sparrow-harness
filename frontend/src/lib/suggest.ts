/**
 * Suggestion source for the prompt box's autocomplete rows.
 *
 * Backed by the real POST /suggest (Interviewer.suggest, Tier.CHEAP — see
 * backend/src/sparrow/agents/interviewer.py). That route never raises; it
 * returns `{ suggestions: [] }` on any failure so a broken completion can't
 * interrupt typing, which is why this wrapper doesn't need its own retry
 * logic — just pass the failure through and let the caller no-op it.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Suggestion = {
  id: string;
  /** The completed prompt text, shown as the row's main line. */
  text: string;
  /** What category this expands into, shown as a small trailing hint. */
  category: string;
};

/**
 * Returns up to `limit` candidates for the given partial prompt. Rejects
 * with an AbortError if `signal` fires first — callers cancel on every new
 * keystroke since the backend call takes several seconds.
 */
export async function suggest(
  query: string,
  signal?: AbortSignal,
  limit = 5
): Promise<Suggestion[]> {
  const res = await fetch(`${API_URL}/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ q: query, limit }),
    signal,
  });

  if (!res.ok) return [];

  const data: { suggestions?: Suggestion[] } = await res.json();
  return data.suggestions ?? [];
}

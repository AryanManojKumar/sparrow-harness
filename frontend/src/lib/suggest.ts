/**
 * Suggestion source for the prompt box's autocomplete rows.
 *
 * Mocked until the backend's POST /suggest exists (Tier.CHEAP, see
 * backend/src/sparrow/providers.py). The signature is shaped to match what
 * that route will return, so swapping the body for a fetch() is a one-file
 * change — nothing that calls suggest() needs to know it happened.
 */

export type Suggestion = {
  id: string;
  /** The completed prompt text, shown as the row's main line. */
  text: string;
  /** What category this expands into, shown as a small trailing hint. */
  category: string;
};

const FIXTURES: Suggestion[] = [
  {
    id: "b2b-saas",
    text: "a B2B SaaS platform — pricing table, logo wall, integration grid",
    category: "B2B SaaS",
  },
  {
    id: "local-service",
    text: "a local service business — quote form, service area, hours",
    category: "Local service",
  },
  {
    id: "portfolio",
    text: "a design portfolio — case studies, process, contact",
    category: "Portfolio",
  },
  {
    id: "commerce",
    text: "a small commerce storefront — product grid, checkout, reviews",
    category: "Commerce",
  },
  {
    id: "agency",
    text: "an agency site — services, case studies, team, contact",
    category: "Agency",
  },
];

function scoreAgainst(fixture: Suggestion, query: string): number {
  const q = query.toLowerCase();
  const hay = `${fixture.text} ${fixture.category}`.toLowerCase();
  if (hay.includes(q)) return 2;
  const words = q.split(/\s+/).filter(Boolean);
  const hits = words.filter((w) => hay.includes(w)).length;
  return hits / Math.max(words.length, 1);
}

/**
 * Returns 0–5 candidates for the given input, ranked loosely against it.
 * Resolves after a short simulated network delay; rejects with an
 * AbortError-shaped error if `signal` fires first, matching fetch()'s
 * contract so callers don't have to branch on mock-vs-real.
 */
export function suggest(query: string, signal?: AbortSignal): Promise<Suggestion[]> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("aborted", "AbortError"));
      return;
    }

    const timer = setTimeout(() => {
      const ranked = FIXTURES
        .map((f) => ({ f, score: scoreAgainst(f, query) }))
        .filter(({ score }) => score > 0)
        .sort((a, b) => b.score - a.score)
        .map(({ f }) => f);

      resolve(ranked.length ? ranked : FIXTURES.slice(0, 3));
    }, 260);

    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("aborted", "AbortError"));
    });
  });
}

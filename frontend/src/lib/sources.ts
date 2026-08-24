/**
 * Reference-site lookup for an accepted suggestion.
 *
 * Mocked — stands in for the real `sources` pipeline (scout + rank, see
 * CLAUDE.md §5 and backend/src/sparrow/scout.py), which won't run until a
 * project actually exists. This exists so the "here's a reference this
 * suggestion drew from" citation can be designed and wired end to end now;
 * swap `sourceFor` for a real lookup once /suggest (or a follow-up call)
 * returns one.
 */

export type Source = {
  id: string;
  title: string;
  domain: string;
  url: string;
  description: string;
};

const CATALOG: { keywords: string[]; source: Source }[] = [
  {
    keywords: ["saas", "b2b", "software", "platform", "dashboard"],
    source: {
      id: "linear",
      title: "Linear",
      domain: "linear.app",
      url: "https://linear.app",
      description: "B2B SaaS reference — pricing, feature grid",
    },
  },
  {
    keywords: ["plumb", "hvac", "repair", "clean", "local", "contractor"],
    source: {
      id: "angi",
      title: "Angi",
      domain: "angi.com",
      url: "https://www.angi.com",
      description: "Local service reference — quote form, service area",
    },
  },
  {
    keywords: ["portfolio", "design", "studio", "creative"],
    source: {
      id: "dribbble",
      title: "Dribbble",
      domain: "dribbble.com",
      url: "https://dribbble.com",
      description: "Portfolio reference — case-study pacing",
    },
  },
  {
    keywords: ["salon", "groom", "pet", "spa", "wellness"],
    source: {
      id: "rover",
      title: "Rover",
      domain: "rover.com",
      url: "https://www.rover.com",
      description: "Pet-service reference — booking, trust signals",
    },
  },
  {
    keywords: ["restaurant", "cafe", "food", "menu", "catering"],
    source: {
      id: "toast",
      title: "Toast",
      domain: "toasttab.com",
      url: "https://pos.toasttab.com",
      description: "Food-service reference — menu, ordering flow",
    },
  },
  {
    keywords: ["commerce", "shop", "store", "product", "retail"],
    source: {
      id: "shopify",
      title: "Shopify",
      domain: "shopify.com",
      url: "https://www.shopify.com",
      description: "Commerce reference — product grid, checkout",
    },
  },
  {
    keywords: ["agency", "consult", "marketing"],
    source: {
      id: "clay",
      title: "Clay",
      domain: "clay.global",
      url: "https://clay.global",
      description: "Agency reference — services, team, contact",
    },
  },
];

const FALLBACK: Source = {
  id: "stripe",
  title: "Stripe",
  domain: "stripe.com",
  url: "https://stripe.com",
  description: "General reference — structure and pacing",
};

export function sourceFor(input: { text: string; category: string }): Source {
  const hay = `${input.text} ${input.category}`.toLowerCase();
  for (const { keywords, source } of CATALOG) {
    if (keywords.some((k) => hay.includes(k))) return source;
  }
  return FALLBACK;
}

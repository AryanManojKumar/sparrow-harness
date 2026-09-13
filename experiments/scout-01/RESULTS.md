# scout-01 — can we segment real sites at all?

The per-section ranking design depends on finding sections before ranking them.
So that was tested first, on three live B2B SaaS sites: linear.app, resend.com,
vercel.com.

## Attempt 1 — visual bands only: total failure

Heuristic: full-bleed elements over 180px tall, outermost of any nested run.

**All three sites collapsed to a single band containing the whole page.** Linear:
one div, 10,898px. Resend: one div, 12,045px. Real pages nest wrappers 3–6 deep,
and descending one level was not enough.

Notable in hindsight: all three sites **do** use `<section>` — 9, 12 and 10 of them.
The heuristic had ignored the author's own segmentation in favour of guessing.

## Attempt 2 — semantic first, spine descent as fallback

1. If ≥3 visible `<section>` elements exist, use them, then pull in `header`/`footer`
   left outside. Most well-built sites qualify.
2. Otherwise descend the DOM while a single full-bleed child swallows the page, up to
   12 levels, until reaching a node with several tall siblings.

| Site | Bands | Result |
|---|---|---|
| linear.app | 9 | clean — nav, 7 sections, footer |
| resend.com | 12 | clean — headings read as real section names |
| vercel.com | 6 | **partial — 3 sections came back with 0 words** |

Vercel is the honest failure: one band is 2,418px tall with 56 words. Content behind
lazy rendering or an animation gate that a scroll pass did not trigger. **Expect
roughly one site in three to need a fallback.**

## Classification — works, and is effectively free

A cheap-tier model labelling bands from structure alone (height, word count, image /
button / list counts, headings) — no screenshots:

**$0.00292 for all three sites.**

Resend came out essentially perfect: nav · hero · logo-wall · integration-grid ·
feature-grid · product-showcase · feature-grid · feature-detail ×3 · testimonial · cta.

Two behaviours worth keeping:
- It labelled Vercel's empty bands `other` rather than inventing a type, because the
  prompt told it to. Refusing to guess is the correct behaviour and it was learned
  from the inspector's false positive.
- Linear's hero was mislabelled `feature-grid` — that hero carries 61 images and 38
  buttons, so structurally it does not look like one. Position matters as much as
  shape; the classifier should be told band 1 is a hero candidate by default.

Accuracy is roughly 85%, with low-confidence flags landing on the genuinely ambiguous
cases.

## Follow-up — the "empty sections" were never empty

Vercel's four blank sections looked like a scraper-capability problem. They were not.

Patient waiting changed nothing — 600ms dwell, two passes, `networkidle`, fonts loaded:
identical output, 124 words, four blanks. So not a timing problem either.

Inspecting them showed `textContent` holding 598, 582, 56 and 40 characters. The copy
was in the DOM the whole time. **`innerText` reports only RENDERED text**, and those
sections were sitting at `opacity: 0` behind an animation gate that never fired for a
headless viewport.

One-word fix — fall back to `textContent`, and flag that it was needed:

| Site | Before | After |
|---|---|---|
| vercel.com | 6 bands, 4 empty | 6 bands, **0 empty** (3 recovered) |
| linear.app | 9 bands, 0 empty | unchanged, 0 recovered |

The `unrendered` flag is worth keeping rather than hiding: a band whose text exists but
does not render is exactly the band whose screenshot will also be blank, so it should
be ranked on structure rather than on pixels.

**This settles the scraper question.** It was never a capability gap. A text-extraction
API would have hit the same wall — most call `innerText` or serialise rendered output —
and would additionally have given up computed styles and element geometry.

## Scraper evaluation — crawl4ai, and what the block rate actually is

crawl4ai (79k stars, Apache-2.0, actively maintained) **depends on
`playwright>=1.49`**, plus `patchright` and `playwright-stealth`. It is a Playwright
wrapper, so there is no browser capability in it we do not already have.

What it adds: stealth/anti-bot, markdown extraction, BM25 filtering, sqlite caching,
LLM extraction strategies, session management.

What it costs for this use case: `CrawlResult.screenshot` is **one page-level string**.
There is no persistent page handle, so no per-element screenshots and no multi-breakpoint
capture in a single session — which is exactly what per-section ranking and
interview-by-screenshot need.

Then the empirical question: are we actually being blocked? Nine live sites:

**0 blocked. 0 empty sections.** Stealth solves a problem we do not have.

The real failure was segmentation. Three of nine came back with 1–2 bands, and the
diagnosis was that the spine descent stopped too early — clerk.com yields two children
of `<body>`, one of which is 7,059px of a 7,674px page. Still a wrapper, not a section.

Fixed by descending **recursively**: any child taller than 55% of the page is a
container by definition, so recurse into it and keep its siblings.

| Site | strategy | before | after |
|---|---|---|---|
| clerk.com | spine | 2 | **8** |
| www.twilio.com | spine | 2 | **10** |
| www.datadoghq.com | spine | 5 | 5 |
| posthog.com | spine | 1 | 1 — still thin |

**Usable: 3/9 → 8/9.**

posthog.com remains the one honest failure, and it is a different class: its page is
900px tall at load — an `h-dvh` app shell that renders on interaction. No scraper fixes
that; it needs interaction scripting or exclusion.

**Verdict: stay on Playwright.** The win came from a recursive descent and a
`textContent` fallback — twelve lines of our own code. If blocking ever appears, adopt
`patchright` directly: it is a drop-in Playwright replacement, one import, and it keeps
the page handle.

## What this means for the ranking design

Segmentation and classification are both **viable and cheap**. The chain
*segment → classify → rank* is reachable.

The real risk was never the ranking logic — it is extraction fidelity, and it shows up
as empty sections on client-heavy sites. That needs a fallback before ranking is worth
building: retry with a longer settle, then fall back to screenshot-only ranking for
bands whose text never arrives.

## Next

- Commonality across sources (deterministic — count section types across sites)
- Per-section ranking against the brief, with a concrete rubric rather than "which is best"
- Interview-by-screenshot at the design gate

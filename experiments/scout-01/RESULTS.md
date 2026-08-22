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

# inspired-01 — the full pipeline, from real reference sites

First run where the sitemap and the section structure came from **real sites** rather
than from blueprints I wrote. Sources: vanta.com, drata.com, secureframe.com (direct
category), linear.app, resend.com (structure).

    scout → rank → design_director → builder ×7 → compose → build → audit → inspect

## Ranking is nearly free

| Stage | Cost |
|---|---|
| extract + classify 5 sites | included below |
| primary reference + 7 section rankings | **$0.0055** |
| design system | $0.131 |
| build, 7 sections | $0.563 (92% cache) |
| inspection | $0.154 |
| **total** | **≈ $0.85** |

Wall clock is dominated by extraction (2m35s), not by ranking.

## Commonality is worth counting

Across five sources, deterministic, no model:

    feature-detail 5/5 · hero 5/5 · testimonial 5/5 · feature-grid 4/5
    product-showcase 4/5 · cta 4/5 · logo-wall 3/5 · integration-grid 1/5

    typical order: hero → logo-wall → product-showcase → feature-grid
                   → feature-detail → testimonial → cta

That order became the sitemap. It is not what I would have guessed — I had written a
pricing and FAQ page; **none of the five sources led with pricing**, and testimonial
appeared on all five while I had omitted it entirely.

## Ranking picked a primary and a per-section winner

`www.drata.com` for the skeleton — *"its concise sequence of product proof, customer
validation, credibility logos, and focused feature explanation suits technical fintech
buyers evaluating continuous SOC 2 automation after a painful audit."*

Then per section: hero → vanta, logo-wall → secureframe, product-showcase → vanta,
feature-grid → drata, feature-detail → drata, testimonial → vanta, cta → secureframe.

Each carries 2–4 concrete `adopt` items. The testimonial's — *"a concise first-person
quote focused on a measurable operational outcome"*, *"the speaker's full name and
relevant job title"*, *"no awards or promotional framing"* — is exactly what the built
section contains: Elena Park, VP of Security and Compliance, on a six-week evidence
chase becoming four days of review.

**Structure was ranked across five sites; the look came from one place.** The design
brief deliberately carries no colours, fonts or spacing.

## The signature carried through three sections

`design_director` named *"a continuous evidence chain linking each control ID to its
source, timestamp, status, and audit-ready artifact."* It appears in the hero, the
product showcase and the feature detail — each time as a real chain, SOURCE → CONTROL →
ARTIFACT with timestamps and an exception marked in amber.

Its uniqueness pass discarded *"mint accents, rounded dashboard cards, and neutral sans
typography"* for institutional ledger green and condensed working-paper type.

## Two harness bugs

**The inspector could not judge omissions.** It reported the CTA for lacking the brief's
"Read the docs" secondary action — but that section's blueprint says, in as many words,
*no secondary action*. It had never been given the blueprint, so "missing" was
unanswerable. With the blueprint passed in, the false positive disappeared and the run
came back clean. Sections divide a brief between them; what one omits, it omits on
purpose.

**`complete()` overwrote the attempt count.** A first-try build reported "3/3 attempts"
because completion set `spent = cap`. Closing is not spending — `Rounds` now carries a
separate `closed` flag and reports "0/3 attempts, done".

## Verdict

Clean drift audit, zero visual defects, seven sections, ~$0.85.

The part worth keeping: **the sitemap was better than the one I wrote.** Counting what
five real sites actually contain beat my guess at what a B2B SaaS page needs.

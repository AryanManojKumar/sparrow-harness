# dsh-builder-02 — FPS: free agent vs Sparrow's brain

2026-11-01. New project `fps-shooter` (MananShooter as a tactical FPS, same no-invention
rules as the earlier MananShooter runs). Sources: counter-strike.net/cs2,
playvalorant.com, reachthefinals.com. Sparrow's upstream ran for real and was halted at
BUILD (`brain.py`); Sparrow's builder never ran. All builds used the identical studio
loop on gpt-5.6-terra. Reproduce with `../dsh-builder-01/run.py` and
`EXP_SRC=fps-shooter EXP_PREFIX=fps EXP_OUT=../dsh-builder-02/out`.

- **B** — free agent: prompt, every source band, the logo. Designs everything.
- **C** — Sparrow's build plan to the letter.
- **C+** — same brain, plan reframed as material ("you own the craft"), all source
  bands, guardrails kept.
- **B+** — free agent + Sparrow as materials and guardrails (curated assets, FACTS.md,
  brand rule), no section plan. First two attempts were refused upstream (the VoiceOwl
  APIM subscription's $50 weekly cap); run on 2026-11-02 after the reset.

| | B | C | C+ | B+ |
|---|---|---|---|---|
| Time · model calls | 374 s · 16 | 364 s · 20 | 351 s · 25 | 272 s · 14 |
| Sections · height | 8 · 5341 px | 5 · 5138 px | 5 · 4710 px | 9 · 6231 px |
| Imagery | 3 self-generated, no video | 8 + hero video | 10 + hero video | 14 curated + hero video |
| Invented facts | map names, a fake "02:14" trailer | 1 | platform badges (from Sparrow's content stage) | none found |
| Broken links | 0 | 3 | 0 | 0 |
| Closest reference colour (ΔE, `brand.py`) | 10.6 to THE FINALS' red, 10.2 to VALORANT's | 81.6+ | 81.6+ | 62+ (own midnight/acid-green) |

The owner's verdict before B+: **B looks best.** B+ keeps B's design energy (editorial
type, a cream band against the dark, varied sections) and fixes all three of its flaws.

## Findings

- **B wins on looks, and part of how it wins is copying.** Its red/cream/black lands
  ΔE ≈ 10 from VALORANT's and THE FINALS' reds — the same colour to most eyes — which
  is the reproduction §5 says a harness must not do. It also faked a trailer and named
  maps nobody gave, and used none of the curated assets or video.
- **C and C+ build what the plan says, and this plan was the weaker design.** Five
  sections and a boxed feature field came from Sparrow's composer; "you own the craft"
  in a preface did not move the agent off a 35 KB plan that describes five sections
  in detail. C+ only improved the headline.
- **The brain's value is materials and guardrails, not layout taste:** real assets and
  video, its own palette, honest facts (mostly). Its weakness is the composer/design
  taste — and one content-stage invention (platform badges) that reached the page
  because the asset gate was answered without confirming it.
- **Scout gap:** VALORANT's recorded palette has no saturated colour — its red was
  missed, so the brand check against it used the public brand colour by hand.
- **Harness bug found and fixed:** a model that never answers (here: budget cap) ended
  the studio turn as "done, nothing changed". It now surfaces as an error
  (`studio.ModelUnavailable`, with a test).

- **B+ is the answer.** A free agent designing from the references, held by Sparrow's
  curated assets, a facts sheet and the brand rule, produced the best page of the
  experiment — B's craft, its own palette (ΔE 62+ from every reference), all curated
  imagery and the real video (the trailer button opens it), nothing invented, in the
  fewest calls.

## Decision

DeepSeek designs and builds; Sparrow scouts, curates, holds the facts and guards. The
composer's per-section plan is dropped from the critical path; its measurements remain
available as reference. One caveat: one run on one project — the first real run of the
new pipeline should be a different category (a B2B brief).

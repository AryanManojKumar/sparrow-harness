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
  brand rule). **Not completed:** the VoiceOwl APIM subscription hit its $50 weekly cap
  mid-experiment; both attempts were refused upstream.

| | B | C | C+ |
|---|---|---|---|
| Time · model calls | 374 s · 16 | 364 s · 20 | 351 s · 25 |
| Sections · height | 8 · 5341 px | 5 · 5138 px | 5 · 4710 px |
| Imagery | 3 self-generated, no video | 8 + hero video | 10 + hero video |
| Invented facts | map names, a fake "02:14" trailer | 1 | platform badges (from Sparrow's content stage) |
| Broken links | 0 | 3 | 0 |
| Closest reference colour (ΔE, `brand.py`) | 10.6 to THE FINALS' red, 10.2 to VALORANT's | 81.6+ | 81.6+ |

The owner's verdict: **B looks best.**

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

## Next

Run B+ when the budget resets — it is the test of "DeepSeek designs, Sparrow scouts,
curates and guards". Setup is ready (`run.py setup bplus`).

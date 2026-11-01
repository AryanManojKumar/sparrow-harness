# dsh-builder-01 — does Sparrow need its own builder, or only its brain?

2026-11-01. Same brief, sources and owner material (voiceowl). B and C ran through
the identical studio loop (edit → build → look → one checkpoint) on the same model
(gpt-5.6-terra via the gateway), so the only variable is what the agent was given.
`run.py` reproduces every number here.

- **A** — Sparrow end to end: the original pipeline output, untouched.
- **B** — DeepSeek Harness from a prompt + sources: build rules, 38 source band
  screenshots, the owner's uploads, a request written as a user would type it.
- **C** — Sparrow's brain + DeepSeek's hands: tokens, fonts, curated assets, and per
  section the blueprint, composition block, identity block, verbatim copy, assets and
  winning source band (BUILD_PLAN.md, 57 KB), with the builder's sections removed.

| | A | B | C |
|---|---|---|---|
| Build time | builder + verify loop | 382 s | 452 s |
| Model calls to build | 83 (builder/inspector/fixer/repairer, cumulative over rebuilds) | 20 | 29 |
| Sections · height | 10 · 9030 px | 11 · 5474 px | 10 · 8732 px |
| Owner files used | 4 img + 1 video | 2 img + logo, no video | 3 img + logo + 1 video |
| Unconfirmed claims (`audit.unconfirmed`) | 1 | 16 | 4 |
| Confirmed copy kept verbatim | yes | no — rewrote all | yes |
| Broken links (`store.broken_links`) | 31 | 0 | 23 |
| Code | 12 files, 74 KB | 1 file, 11 KB | 12 files, 26 KB |

## Findings

- **B is the most polished at a glance and the least this company's.** It rewrote
  every confirmed line, invented claims ("WhatsApp", "© 2025", FAQ answers), dropped
  both videos and a screenshot, and chose its own palette — the Emergent pattern from
  the 2026-09-13 head-to-head (high polish, low identity). One 10 KB file is also a
  poor base for section-by-section studio edits.
- **C reproduces A almost exactly** — structure, copy, measured design, real assets —
  in one agent session instead of the builder's per-section calls and repair rounds.
  The identity lives in the brain; the hands are replaceable.
- **A and C share the dead-link gap; B avoided it by owning its nav.** Sections carry
  no `id`s and the nav links to pages that were never made. A build-plan rule (and the
  studio's "Complete the site") is the fix, not a different builder.
- **Caveat:** C's time replaces only BUILD + VERIFY; scout, design, content and asset
  stages still run before it. Dollar cost for B/C is unknown — the gateway does not
  meter usage yet.

## Decision it points to

Keep Sparrow's upstream (scout, design director, composer, content editor, curator,
gates); replace builder + inspector + fixer + repairer with one DeepSeek Harness
session driven by the build plan, which then continues as the studio on the same site.

Shots: `shots/{a,b,c}-home-*.jpg`. Raw: `run-{b,c}.json`, `events-{b,c}.jsonl`,
`measure-{a,b,c}.json`.

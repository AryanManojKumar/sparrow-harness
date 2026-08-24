# curator-01 — real imagery in the page

`curator` produces the imagery blueprints ask for, and records what may be claimed about
each one.

## Two paths, deliberately asymmetric

**GENERATED** — from a blueprint's asset brief, for a product with nothing to screenshot.
Its contents are invented by construction. Gating that would gate the mechanism, so it
is not gated.

**RESTYLED** — the user's own screenshot, restyled to the design system. Still a picture
of their real product, so text the model adds is a claim they never made. Gated.

`Provenance` on every asset: `user_supplied` / `restyled` / `generated`.

## The fidelity gate catches what a visual diff cannot

Validated against the known-bad pair from image-probe-02, where a chat widget had
truncated three paragraphs and the model completed them:

    verdict : REJECT
    invented: adapt, collect, empower, evidence, features, frameworks,
              grow, streamline, visibility, workflow
    control (same image against itself): PASS

Every word I had found by hand, plus six more from a paragraph I had not checked.

Compared at **word** level, not line level — a restyle legitimately reflows text, so
line breaks move. Only *invented* words reject; *lost* words do not, because removing a
cookie banner is the point.

## In the page

Four assets generated for ide-01, each with three deterministic variants (hero, card,
mobile — Pillow, no model, no cost). The hero asset is a convincing pull-request
interface: real TypeScript, proper hunk headers, agents with commit hashes and +/- counts,
CI checks with durations. It named the product "Working Tree" — picked up from the design
system's own background colour name, which nobody asked for.

Rebuilt with the asset passed in:

| | hand-drawn | with real asset |
|---|---|---|
| lines | 269 | 184 |
| `<div>` count | ~90 | **12** |
| product imagery | CSS pretending to be a UI | `next/image`, real capture |

The builder wrapped it in chrome per `imagery_treatment` — a run header reading
`ACME/PLATFORM · RUN_8F2A`, and a footer strip `SRC/RUNNER/SCHEDULER.TS · +42 −11 ·
APPROVAL REQUIRED`. The amber accent appears exactly once.

## A placement bug worth recording

The assets block first went into `stable_system`, the cached prefix. Assets vary per
section, so that would have broken prefix caching on every call — the 92% hit rate would
have gone to zero, silently. Anything that varies per call belongs in the user message;
the system block is for what is identical across all of them.

## Not done

Only the hero was rebuilt. A full rebuild with assets across all six sections has not
run. Five of the nine asset briefs have no image yet (`--limit 4`).

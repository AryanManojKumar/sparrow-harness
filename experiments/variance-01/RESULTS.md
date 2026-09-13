# variance-01 — the design agent has none

Prompted by a fair observation: the second ide-01 build looked like the first, despite
generated blueprints replacing hand-written ones. Coincidence, or the pipeline?

Neither. **The design agent is deterministic.**

## Measurement

Three independent `direct()` calls, identical brief and sources:

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| fonts | Recursive / Public Sans / Geist Mono | identical | identical |
| ground | `oklch(0.965 0.014 232)` "Working Tree" | identical | identical |
| primary | `oklch(0.455 0.128 239)` "Branch Blue" | identical | identical |
| signature | The Review Gutter | The Review Gutter | The Review Gutter |

Byte-identical to three decimals. The only movement was one word of signature prose,
"diff-style" versus "diff-derived".

So the two ide-01 builds looked alike because **the design system determines look, and it
did not change between them**. Generated blueprints changed section density and content;
they could not change direction.

## Why this matters, and not for the obvious reason

Determinism is good for CLAUDE.md §3 — a run is replayable, a regression traceable.

It is fatal at Gate 2. §8 puts a human approval on the design direction, and a user who
says "not this" was getting the identical proposal back. Rejection had no effect, because
nothing about the inputs changed and re-rolling is not a change.

**Divergence has to be instructed.** This is the branch/replace split Superdesign uses:
branch explores alternatives, replace refines the chosen one. Re-running is neither.

## The fix

`direct(..., avoid=[...])` passes rejected directions back and rules them out, with an
explicit instruction to change the argument rather than the adjectives.

| | signature | ground hue | primary | type |
|---|---|---|---|---|
| 1 | The Review Gutter | 232 | Branch Blue | Recursive / Public Sans |
| 2 | The Landing Graph | 145 | Dependency Teal | Saira Semi Condensed / Commissioner |
| 3 | The Merge Docket | 20 | Authorization Carmine | Geologica / Source Sans 3 |

Different ideas, not restyles. Alternative 2: *"an unlabeled topology diagram could belong
to any infrastructure product, so it became a repository-specific Landing Graph."*
Alternative 3: *"rejected another coordination map or persistent diff treatment as the
predictable answer for an agent harness."*

Cost: $0.12–0.13 per alternative.

## Implication for Gate 2

Present **two or three directions at once**, not one to approve or reject. A business
owner can answer "which of these"; they cannot usefully answer "is this good". Same
react-don't-compose principle as the content interview, now with a mechanism behind it.

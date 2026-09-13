# Drift test — results

**Question.** Does an injected design system hold when each section is built by an independent
model call with no memory of the others? (`AGENTS.md` §12; `CLAUDE.md` §6 "falling apart in its
lower third".)

**Method.** Five agents, run in parallel, each given brief + constraints + design-system +
its own blueprint only. None could see any other section's code. 636 lines produced.
Fixed design system, hand-written — no design agent involved. Verdict by grep, then by eye.

---

## PASS — vocabulary held, essentially completely

| Check | Spec | Result |
|---|---|---|
| Literal colour utilities | zero | **0** |
| Blue anywhere | banned — "our competitor is blue" | **0** |
| Font weight > 600 | banned | **0** |
| `framer-motion` import | banned, use `motion/react` | **0** — 5/5 correct |
| Shadows | `shadow-sm` rest, `shadow-md` hover | only those two |
| Accent uses per section | ≤ 1 | 1, 1, 1, 0, 0 |
| Display type step | hero headline **only** | used exactly once, in the hero |
| Section padding | `py-24 md:py-32` | all four full sections; logo wall used half, as its blueprint asked |
| Container | `max-w-6xl` | all five |

The `motion/react` result is the strongest single signal: training data is saturated with
`framer-motion`, and all five independently used the new path. An explicit ban propagates.

The display-step result is the second: four agents who never saw the hero all stayed off
`text-5xl` because the design system said it belonged to the hero.

## LEAKED — three categories, all where the spec named a scale but never closed it

| Leak | Count | Where |
|---|---|---|
| `text-lg` | 4 | LogoWall wordmarks — off the declared type scale |
| `gap-2` / `gap-3` / `gap-4` | 6 | all inline flex gaps; the spec only defined *grid* gap |
| `rounded-full` | 2 | 6px status dots in the hero |

The pattern is consistent and useful: **enumerated closed sets held perfectly; open-ended
scales leaked.** "Nine values. There is no tenth." held. "Weights 400/500/600 only, never 700
or above" held. "Grid gap `gap-8`" did not cover inline gaps, so agents invented them.

**Fix:** state every scale as a closed enumeration with the boundary spelled out, the way the
palette and weight rules were. Add inline-gap and wordmark steps rather than leaving the gap.

## FAILED — one real defect, invisible from inside any single section

**Pricing and FAQ both chose the muted ground, and they are adjacent.** They merge into one
undifferentiated grey block roughly a third of the page tall. Each section is correct on its own;
the pair is wrong.

No agent could have caught this — neither could see the other. This is precisely the class of
defect `observer` exists for, and the first empirical evidence that whole-page review is not
optional. It also validates scoping `observer` to cross-section coherence rather than taste.

**Fix:** section ground belongs to `sitemap` (owned by `design_director`), not to the builder.
Alternation is a page-level decision.

## Harness lesson — capture

The first screenshot pass showed sections 3–5 as **blank**. Cause: `whileInView` entrance
animations start at `opacity: 0` and never fire, because `fullPage` capture does not scroll.

**`inspector` must scroll the full page before capturing**, or it will report false "empty
section" defects on every animated site it ever looks at. Encoded in `shots/` capture script:
step through at half-viewport increments, 120ms dwell, return to top, then shoot.

## Verdict

The thesis holds. **Vocabulary constraints propagate across independent builds; composition
decisions do not.** That is the argument for both halves of the architecture — inject the design
system to prevent token drift, and keep a whole-page observer for the coherence failures that no
section-local agent can see.

Artifacts: `shots/desktop-full.png`, `shots/mobile-full.png`, `workspace/src/components/sections/`.

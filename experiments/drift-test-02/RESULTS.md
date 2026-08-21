# drift-test-02 — the real builder, on OpenAI

Same brief, same design system, same blueprints as `drift-test-01`. Different in two
ways: built by `sparrow build` (the actual harness, not hand-driven subagents), and
by `gpt-5.6-sol` instead of Claude.

**Two variables changed at once**, so this is not a clean model comparison. The
design system was also repaired after drift-test-01 — closed enumerations, and
`inline_gap` defined. Read the clean audit as validating that fix at least as much
as the model.

## Result

| | drift-test-01 | drift-test-02 |
|---|---|---|
| Builder | subagents, hand-driven | `sparrow build` |
| Model | Claude | `gpt-5.6-sol` |
| Lines | 636 | 706 |
| Drift findings | 9 | **0** |
| Build | passed first try | failed, repaired, passed |
| Cost | not metered | **$0.43** + $0.07 repair |
| Wall clock | ~90s (parallel) | ~3m30s (serial) |

Measured token use per section: **~1,400 in, ~1,800–4,900 out**. Output ran well above
the 1,299 estimated from drift-test-01's file sizes, because reasoning models spend
tokens before emitting any — worth remembering when budgeting.

## Finding 1 — the model imported an icon that no longer exists

`Hero.tsx` imported `Github` from `lucide-react`. All brand icons were **removed in
lucide v1**; the pinned version exports 6,095 names and that is not one of them. The
bundler's guess was *"Did you mean to import Gift?"*

The drift audit cannot catch this. It is a well-formed import of a real package that
resolves to nothing, and only a build reveals it. **A section is not done when it is
written; it is done when it compiles.**

This is also the predicted failure of a pinned dependency whose API moved out from
under the training data — the same shape as CLAUDE.md §9's argument against runtime
framework selection, arriving through a different door.

## Finding 2 — a directive phrased as a fact is ignored

Section ground moved to `sitemap` after drift-test-01. The prompt said:

> ground: this section sits on the muted ground (`bg-muted`) — decided at page level, not by you

**Four of five sections ignored it**, emitting no ground class at all. The page came
out flat, with no section rhythm — the drift-test-01 defect in a new costume.

The model read a statement of fact as background information. Rewritten as an
instruction with the consequence named:

> REQUIRED: the root `<section>` element MUST carry the class `bg-muted`. Section
> ground alternates across the page and is decided at page level — it is not yours to
> choose, and omitting it flattens the page rhythm.

**Five of five complied.** Same information, same model, same everything else.

This generalises past the ground class: a constraint stated declaratively reads as
context. It has to be an imperative with a consequence attached.

## Finding 3 — the repair loop works, and belongs to a separate agent

`Repairer` is deliberately not `Builder`. The builder makes design decisions; the
repairer makes the smallest change that clears a named error. One agent holding both
jobs will redesign a section while "fixing" an import. Capped at 3, like every other
loop.

First real repair: build error in, corrected file out, one attempt, $0.0696.

## Verdict

The engine runs end to end: workspace from scaffold → tokens rendered from the
blackboard → five independent builder calls → build → repair on failure → drift audit
→ scroll-then-capture. Clean audit, coherent page, $0.43.

Artifacts: `sections/`, `shots/desktop-full.png`.

# flow-01 — why the output does not flow like the sources

The question was whether building section-by-section prevents the continuity real sites
have, and what to do about it. Three fixes were on the table: give each builder its
neighbour's edge, add a composition pass, or have the design system name a cross-section
motif.

Measured first. None of them was the answer.

## What the sources actually do

    wise.com/business    sections 8    groundChanges 0    distinctGrounds 1
    stripe.com/connect   sections 10   groundChanges 0    distinctGrounds 1
    linear.app           sections 7    groundChanges 0    distinctGrounds 1

    ours                 sections 9    groundChanges 6    distinctGrounds 2

**All three use ONE ground for the entire page.** Not one of them alternates.

Boundary-crossing elements exist but are rare — 9 on stripe, 3 on linear, 0 on wise — so
the elaborate options were solving a problem the sources do not have. What separates their
pages from ours is not connective tissue across boundaries. It is that ours is banded into
nine visible blocks and theirs is one surface.

## The alternation was mine, and it was a fix for something else

After drift-test-01, two adjacent sections independently chose the muted ground and merged
into one grey slab. I fixed that by moving ground to the sitemap and forcing alternation —
a reasonable response to that bug, and the wrong default, imposed without ever checking
what the category does.

## Test

Swapped `bg-muted` to `bg-background` on the four sections that carried it, rebuilt, and
remeasured. No model calls, no cost:

| | before | after | sources |
|---|---|---|---|
| ground changes | 6 | **0** | 0 |
| distinct grounds | 2 | **1** | 1 |
| page height | 10,538px | 9,016px | — |

The page reads as one surface rather than nine stacked panels.

## Implemented

`scout` measures `distinct_grounds` and `ground_changes` per source. The register reports
them — *"3/3 sources use ONE ground for the whole page"* — and the sitemap no longer forces
alternation; every section defaults to the page ground and a design direction can ask for a
change if it wants one.

Same rule as dark/light, motion and saturation: the harness measures, the design agent
decides against the measurement, and no default is imposed on taste.

# ide-01 — a second category, on developer-tool sources

Sources: kiro.dev, cursor.com, deepseek.com/harness, antigravity.google. Brief: an
agent harness for codebases, sold to staff engineers who have already found a coding
agent unreviewable at scale. Constraint list included *"no purple - every dev tool is
purple."*

Run end to end for **$0.70**: scout+rank $0.004, design system $0.128, build $0.567.

## Two ranking bugs the new category exposed

The compliance sources happened to hide both.

**Chrome was being counted as sitemap structure.** `footer` scored 4/4 and `nav` 2/4, so
the "typical order" came out `hero -> nav -> feature-detail -> ...` — nav second. Every
site has a nav and a footer; counting them says nothing.

**`other` was being treated as a section type.** It is the classifier's "I could not
tell" bucket. At 2/4 it crossed the 60% threshold and became a *category convention*,
which turns an extraction failure into a design instruction.

Both now excluded, and reported separately so the count stays visible. The primary
reference **changed** once they were removed — deepseek.com to antigravity.google — so
the noise had been distorting the selection, not just the display.

Final: `hero -> feature-detail -> product-showcase -> testimonial -> feature-grid -> cta`

## The font failure worth catching properly

`design_director` chose **Commit Mono**. It is a real, well-liked typeface that Google
Fonts does not serve. The build failed as:

    Module not found: Can't resolve 'next/font/google/target.css'
    Unknown font

That error lands in `layout.tsx` — **a file no section owns** — so the repair loop, which
maps build errors to section files, could never have fixed it. It would have burned all
three rounds and escalated.

Fixed at the point of choice rather than the point of failure: the Google Fonts catalog
(1,942 families) is fetched and cached, every chosen family checked against it, and any
unknown one sent back to `design_director` with the closest real alternatives. It swapped
Commit Mono for **Geist Mono** and the build passed first try.

The general shape: an agent that names an external resource must have that name validated
before anything downstream depends on it. Same class as the `Github` icon that no longer
exists.

## Result

Signature: *"The Review Gutter — a persistent diff-style vocabulary of line numbers, hunk
brackets, file paths, and amber review checkpoints attached to every product artifact."*

It is on the page throughout: real hunk headers (`@@ -41,6 +41,12 @@`), line numbers,
added/removed lines, file paths, and amber `REVIEW REQUIRED` checkpoints — in the hero,
the feature detail, and the product showcase.

Palette: Working Tree, Repository Ink, Branch Blue, Review Amber. Hue range 78–246, so
nothing in the 280–320 purple band — the constraint held. The uniqueness pass reported
discarding *"the initial dark terminal palette and green success accent [which] resembled
nearly every other agent developer tool."*

The testimonial carries exactly what the ranking said to adopt from cursor.com — a named
speaker with a title and a measured outcome, nothing else: *"median first-review time fell
from 52 minutes to 18." — Maya Chen, Principal Engineer, Northstar Ledger.*

Clean drift audit.

---

# Second pass — generated blueprints

Re-ran with blueprints written by `blueprinter` from the ranked sources, replacing the
hand-written set. **Nothing in the chain is authored by a human now**: brief → scout →
rank → blueprints → design system → build.

Total scout cost including six blueprints: **$0.0105**.

## Generated blueprints produce visibly denser sections

| | hand-written blueprints | generated |
|---|---|---|
| lines | 1,048 | **1,401** |
| build | first try | first try |
| drift | clean | clean |
| cache | 92% | **100% on 5 of 6** |
| cost | $0.567 | $0.682 |

The difference is not length for its own sake. The generated blueprints carry counts and
patterns measured off real pages, so the builder had something specific to build:

- **cta** got 14 slots because the blueprinter observed a two-audience pattern with an
  executable install command on deepseek.com — `command`, `command_copy_label`,
  `individual_label`, `organization_label`. The built section has the install line with a
  copy affordance and a For developers / For organizations split. I would not have
  written that; I wrote "one heading, one button, nothing else".
- **feature-detail** specified sub-points beneath the main explanation, and the build has
  three (plugin boundary, shared event schema, diff provenance) each with its own panel.
- **feature-grid** asked for per-card artifacts, and every card carries a small code or
  config panel rather than an icon.

## Two fixes the first attempt forced

**`slots` meant "image slots" to the model.** The prompt said *"name the image slots
precisely"*, so a hero came back with zero slots and a testimonial with one —
`customer_logo`. Every content slot vanished.

Split into `slots` (copy the builder writes) and `assets` (imagery `curator` will
produce, one sentence each). This is the right shape regardless: two different agents
consume them, and curator now has real briefs waiting — *"one inspectable product capture
showing multiple coding agents working against a shared repository plan with a reviewable
diff before changes land."*

**The visual register changed the design agent's reasoning.** With `2/4 sources
dark-grounded` in the brief, its uniqueness pass now reads: *"A different developer-tool
brief might have led to a dark terminal, neon status color, and generic code-window
imagery. Those defaults were replaced with a cool working-paper field."*

It still chose light — but as a decision it defended, not a default it fell into. Before
the register existed it had no way to know there was a choice.

## What is still missing

Every "product capture" on the page is CSS drawing a fake UI. The blueprints now request
real assets by name and nothing produces them. That is `curator`, and on the evidence —
3/4 sources use video, 2/4 use canvas, 5 large product images per page — it is the
largest remaining gap between this and the sources.

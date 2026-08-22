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

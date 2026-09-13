# inspector-01 — building the vision agent

Built `inspector` and ran it against `drift-test-02`. Four findings, three of them
bugs in what I had already written and was confident about.

## Design

**Per-section screenshots, not full-page.** Arithmetic, not taste: image tokens are
`(w*h)/750` after a 1568px long-edge resize, so a 1440×8690 full-page capture is
squashed to ~260px wide — 543 tokens of unreadable strip. One 1440×900 section is
1,728 tokens and legible. Per-section also lets a defect name its section.

**Deterministic first, always.** Console errors, failed requests, overflow and
contrast are computed before the model is asked anything, and arrive as findings
rather than questions.

**No write capability.** Enforced by never handing it a write tool, so no prompt can
talk it into editing.

Cost: **$0.10 per full inspection** at `gpt-5.6-terra` — 5 sections × 2 breakpoints.

## Finding 1 — my contrast checker was silently wrong

It reported **21 failures at 1.39:1 and 1.52:1** on text that renders perfectly.

Cause: it parsed `getComputedStyle(el).color` with a number regex. Chrome returns
colours in the space the author wrote, and Tailwind v4 tokens are oklch, which
computes to `lab(37.49 -32.00 16.52)`. Read as `rgb()`, that is near-black, so every
ratio collapsed to ~1.4:1.

Fixed by painting the colour to a 1×1 canvas and reading the pixel back — the browser
does the conversion, and it works for any syntax it can parse. Ancestor backgrounds
are composited the same way.

Verified in both directions, which is the part that matters: **0 failures** on the
real design system, and injected pale grey (1.41:1) and mid grey (3.57:1) both caught.
A checker that returns zero may simply be broken in a new way.

## Finding 2 — the vision model invented a design-system violation

First clean run, it reported the FAQ heading was using the hero display step.
It was not — FAQ uses `text-3xl md:text-4xl`, exactly the h2 step, and Hero is the
only section on display. It saw a large heading in a picture and inferred the rest.

**A vision model cannot tell `text-4xl` from `text-5xl`, or one grey from another.**
Prompt now rules out everything the source already answers:

> ANYTHING THE SOURCE ALREADY ANSWERS … You are looking at a picture and you cannot
> tell text-4xl from text-5xl. Every time you have guessed at one, you have been
> wrong. Do not mention the type scale, the palette, or the spacing scale at all.
>
> Your entire value is what ONLY rendering reveals.

The false positive disappeared, and the next run found a real widow instead —
"Production environment · Type II" orphaning "II" onto its own line at mobile.

## Finding 3 — my overflow check missed a page-breaking bug

The vision pass reported, at high severity, that the mobile hero's copy, both
buttons and the entire product panel ran past the right edge and were clipped.
**Confirmed by eye — the section is badly broken at 390px.**

My deterministic check was `documentElement.scrollWidth > innerWidth`, which assumes
overflow makes the page scroll. It does not when an ancestor clips it: content goes
off-screen and the document stays exactly viewport-width.

Rewritten to walk the box model and report the *outermost* overflowing element:

    <div> spans 24px..424px in a 390px viewport — "Continuous SOC 2 compliance…"

It also surfaced two real 404s (`/demo/`, `/docs/`) that nothing had been looking for.

**The vision pass found this first, then it was made deterministic.** That is the
intended direction of travel: vision discovers the class of defect, code takes it
over, and the expensive agent stops paying for it.

## Finding 4 — caching needed 29 more tokens

Nothing cached at all on the builder. The identical prefix was **995 tokens against a
1024-token floor**.

Moving stack, primitives, brief, constraints and design system into the *system*
block took it to 1,082 and caching started immediately: **86–87% hit rate** on calls
2–5.

The ordering rule, now documented in `agents/base.stable_system`:

    SYSTEM = instructions + stack + brief + constraints + design system
    USER   = only what changes (blueprint, section, images)

Honest about the size of the win: it saves ~6% on the builder, because reasoning
models are output-dominated (1,400 in vs 1,265–3,998 out). It matters far more for
the inspector, where a call is ~10,000 input tokens against ~600 output.

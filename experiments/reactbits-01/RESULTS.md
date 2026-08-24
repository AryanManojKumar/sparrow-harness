# reactbits-01 — is a component library the lever for "modern"?

Tested rather than argued. DavidHDev/react-bits, 46k stars, ~160 components across
Animations / Backgrounds / Components / TextAnimations.

## Integration is easier than expected

It installs through **the shadcn CLI the scaffold already uses**:

    pnpm dlx shadcn@latest add @react-bits/DotGrid-TS-TW

Components land as editable source in `src/components/`, not as a dependency. Four
installed clean: DotGrid, SplitText, SpotlightCard, CountUp.

Two costs, both real:

- it added **gsap**, and **downgraded Motion 13 → 12**, silently violating the locked
  stack. Restored by hand; a dependency gate would have caught it.
- `DotGrid` defaults to `baseColor: '#5227FF'` — purple, the exact colour this brief bans.
  But colour is a **prop**, not a literal, on every component checked. They can be driven
  entirely from the palette.

## The builder ignored all four

First rebuild with them available: zero used. Not a failure — the design system's motion
line read *"no ambient loops, parallax, cursor theater, or auto-typing"*, which rules out
DotGrid (ambient) and SpotlightCard (cursor). **The design system excluded them and won.**

That is the architecture working. It also means bolting a component library onto the
project does nothing on its own.

## The real gate is the design director, and it had never heard of them

Added the vocabulary to its prompt — the four components, their props, and the rule that
naming one in `motion` is what makes it available.

Re-run on the original brief: it named all four and **rejected all four**, with a reason —
*"they do not expose a coordination mechanism"*. Correct behaviour: it now notices the
decision instead of making it silently, and the brief it was serving asks for austerity
(*"precise and technical. No hype about velocity."*).

Re-run with the tone loosened to *"confident and kinetic… motion is part of the argument"*:
it **adopted DotGrid** — and repurposed it:

> *"DotGrid powers the Parallel Patchboard as a structured file-by-agent matrix rather than
> an ambient field."*

It still rejected SplitText, CountUp and SpotlightCard. The built hero uses DotGrid as an
agent-selector strip above the product capture, with a footer that reports touched path,
checks and diff state.

## Conclusion

**A component library is not the lever for "modern".** The chain is brief → design
direction → motion vocabulary → build, and the library sits at the far end. An austere
brief produces an austere page no matter what is installed, and that is correct.

The levers, in order of effect:

1. **The brief's tone.** "No hype about velocity" is a request for restraint, and it was
   honoured. Changing that one line changed the whole direction.
2. **Branch mode at Gate 2.** Three directions to choose between beats one to approve.
3. **The component library**, last — useful once a direction asks for it.

Keeping the four installed is cheap and harmless; they are inert unless named.

## Still broken

Ten elements at `opacity: 0` in the new hero. The guaranteed-end-state rule is in the
prompt and this build still shipped `whileInView` without a resolved fallback, so stating
it once was not enough.

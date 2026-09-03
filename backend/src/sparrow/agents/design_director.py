"""The design director.

Decides the direction: atmosphere, signature, palette, type, spacing, motion.
Its output is the vocabulary every builder is then held to.

The prompt is adapted from Anthropic's `frontend-design` skill, which is written
for exactly this job. Three things carried over deliberately:

THE THREE DEFAULTS ARE NAMED. That skill names the looks AI design converges on —
cream/serif/terracotta, near-black with an acid accent, and the broadsheet — and
observes they "appear regardless of subject". A ban list that names the actual
failure beats one that gestures at it, which is the same lesson the builder's
red-flags table encodes.

TWO PASSES, WITH A UNIQUENESS TEST BETWEEN THEM. Plan, then check the plan against
the brief before committing: "work through a similar prompt to see if you arrive
somewhere similar." Any part that would come out the same for a different brief is
not a choice.

BOLDNESS IS SPENT IN ONE PLACE. A named `signature`, with everything around it
quiet. Without it a model distributes interest evenly and the page reads as
templated even when every individual choice is defensible.

The structure of the output follows open-design's DESIGN.md — atmosphere, key
characteristics, named colours with roles. Their 154 shipped systems are brand
clones and must not be shipped as-is (CLAUDE.md §5 draws that line), but the
*shape* is the best-tested format for this artifact.
"""

from __future__ import annotations

import json
import re

from sparrow.agents.base import Agent, context_block
from sparrow.blackboard.schema import Blackboard, DesignSystem
from sparrow.providers import Tier
from sparrow.palette import check as check_palette, report as palette_report
from sparrow.render.tokens import validate_fonts
from sparrow.parse import first_object

SYSTEM = """You are the design lead at a small studio known for giving every client a
visual identity that could not be mistaken for anyone else's. This client has already
rejected proposals that felt templated. Make deliberate, opinionated choices specific to
this brief, and take one real aesthetic risk you can justify.

You are not writing code. You are deciding the VOCABULARY every section of this site will
be built from — and only the vocabulary. Layout, composition and density belong to the
builders. Your job is the palette, the type, the spacing, the motion, and the one idea
that holds it together.

## Ground it in the subject

The subject's own world — its materials, instruments, artifacts and vernacular — is where
distinctive choices come from. A compliance product lives among working papers, audit
trails, controls and evidence. A restaurant lives among menus, produce and service. Go
there for your ideas rather than to a palette generator.

## The signature

Name the single element this page will be remembered by, and make it specific to this
subject.

How much expression surrounds it is NOT your preference to set — it is read from the
sources. The register report measures what this category actually does: how saturated its
brand colours are, whether its pages move, whether they carry video or canvas. Match that
level. A category that is loud gets a loud page; a category that is quiet gets a quiet
one. Cut decoration that does not serve the brief, and do not cut character the category
plainly has.

## Typography carries the personality

Pair faces deliberately — not the ones you would reach for on any other project. Set an
intentional scale with real weights. The type treatment should be a memorable part of the
design, not a neutral delivery vehicle.

## Structure is information

Numbering, eyebrows, dividers and labels should encode something true about the content.
Numbered markers (01 / 02 / 03) are only appropriate if the content actually is a
sequence. Question whether a structural device earns its place before you specify it.

## The three defaults — do not produce these

AI-generated design currently clusters around three looks. All are legitimate for some
briefs, but they appear regardless of subject, which makes them defaults rather than
choices:

1. Warm cream ground (near #F4F1EA), high-contrast serif display, terracotta accent.
2. Near-black ground with a single bright acid-green or vermilion accent.
3. Broadsheet layout — hairline rules, zero border-radius, dense newspaper columns.

If the brief explicitly asks for one of these, follow the brief; its words always win.
Where the brief leaves an axis free, do not spend that freedom on one of these.

Two more template answers to avoid unless the subject genuinely calls for them: a hero
built from a big number with a small label plus supporting stats plus a gradient accent;
and purple or violet as a primary, which is the reflex choice for software.

## Treatments — the open half of this system

Every other field here names a category somebody thought of in advance: colour, type,
spacing, radius, shadow, motion. `treatments` is where everything else goes, and it is
the difference between a page that is correct and a page that is designed.

LOOK AT THE SOURCE SCREENSHOTS AND NAME WHAT THEY ACTUALLY DO TO THEIR SURFACES.
Grain or noise over the ground. A gradient wash bleeding out of one corner. A panel
lifted over the section below it. An image bleeding past the container edge. A backdrop
blur behind a floating bar. A hairline rule that runs the full width while the type stays
inset. A spotlight behind the focal object. Dotted or gridded ground. A masked fade at the
edge of a wide screenshot. None of these have a field above. All of them are why that page
looks made and this one will not without them.

Measured on the last build of this harness: zero gradients, zero backdrop blur, zero
overlapping elements — on a page built from sources that use all three. Not because the
model could not, but because nothing asked and nothing recorded it.

Name three to six. Fewer is a page that reads flat. More is noise.

`how` must be implementable as written — real Tailwind v4 utilities, a real gradient, a
real SVG filter. A treatment named but not specified is a treatment the builder will not
build: "full-bleed" was passed to ten builders as a word and ten of them returned the
default container.

Do NOT reach for a treatment the sources do not support. This is evidence, not decoration.

## The motion vocabulary available to you

These are real components in the project. Colour is a prop on every one, so any of them
can be driven entirely from your palette. Naming one in `motion` is what makes it
available to the builder; the builder will not reach for a technique your motion spec
excludes, and it is right not to.

  SplitText     headline revealed per character or word
  CountUp       a number counting into view
  SpotlightCard a card lit by a cursor-following highlight
  DotGrid       an interactive dot field reacting to the pointer

Decide from the register, not from preference. If the sources move, this page moves; if
they do not, it does not. Banning a technique the category plainly uses needs the same
justification as adopting one it does not. What is not legitimate is
excluding them without noticing you did — a motion spec reading "no ambient loops, no
cursor theater" rules out half this list, so write that only if you mean it.

If you want one, say so in `motion` by name and describe how it behaves in YOUR palette
and at YOUR tempo.

## Work in two passes

FIRST, plan: atmosphere, signature, palette, type, spacing, motion, treatments.

THEN, before you commit, run the uniqueness test on your own plan. Work through what you
would produce for a DIFFERENT brief in the same category. Wherever you would arrive
somewhere similar, that part is a default rather than a choice — revise it, and say in
`revised` what you changed and why.

Only output the plan you arrive at after that pass.

## The palette has to be visible on a screen

Measured across every palette this agent has produced: the two section grounds came out
0.047, 0.050 and 0.055 apart in OKLCH lightness. That is a systematic habit, and below
about 0.06 the alternation between sections is not perceptible — the page reads as one
long block and looks washed out however good the individual choices are.

So, as floors rather than taste:

- `background` and `muted` differ by at least **0.07** in L. They are the two grounds the
  page alternates between; if they cannot be told apart there is no alternation.
- `border` sits at least **0.08** in L from the page ground, or a hairline-led design has
  no visible structure.
- at least one colour carries chroma **≥ 0.11**, or nothing on the page reads as a colour
  and it renders as tinted grey.
- at most **three** colours above L=0.92. Stacked near-white surfaces merge into each other.

These are visibility floors, not a target. How saturated to be above them comes from the
register's measurement of this category, never from preference. A palette whose grounds
are indistinguishable is invisible in any category.

## Scales are closed

Every scale you specify is exhaustive. Whatever you list is all a builder may use, so list
what a real page needs — including the small inline gap, and every type step, not only the
headline ones. A scale with a gap in it will be filled by someone else.

## Output

JSON only. No prose outside it, no code fence.

{
  "atmosphere": "2-4 sentences. What this feels like and why it suits this subject.",
  "signature": "One sentence naming the single memorable element.",
  "key_characteristics": ["4-8 specific, checkable statements"],
  "revised": "What the uniqueness test changed, and why. One or two sentences.",
  "colors": [
    {"token": "background|foreground|primary|primary-foreground|accent|muted|muted-foreground|border|card",
     "name": "an evocative name specific to this subject",
     "value": "oklch(L C H)", "role": "what it is for"}
  ],
  "font_display": "a real Google Fonts family, exact name",
  "font_body": "a real Google Fonts family, exact name; may repeat font_display",
  "font_mono": "a real Google Fonts monospace family, or null if the design has no use for one",
  "font_weights": [400, 500, 600],
  "type_steps": [{"name": "display|h2|h3|body|small|eyebrow",
                  "classes": "exact Tailwind classes",
                  "use": "when to reach for it"}],
  "section_padding": "py-24 md:py-32",
  "section_padding_tight": "py-12 md:py-16",
  "section_padding_loose": "py-32 md:py-48",
  "container": "max-w-6xl px-6",
  "container_wide": "max-w-[88rem] px-6",
  "container_bleed": "w-full",
  "grid_gap": "gap-8",
  "inline_gap": "gap-3",
  "stack_tight": "space-y-4",
  "stack_loose": "space-y-8",
  "radius_base": "0.5rem", "radius_card": "rounded-lg", "radius_input": "rounded-md",
  "radius_full_allowed": "what may legitimately be fully round",
  "shadow_rest": "shadow-sm", "shadow_hover": "shadow-md",
  "imagery_treatment": "how product imagery is presented",
  "motion": "what moves, how far, how long",
  "arrival": "what happens as the reader arrives at a section: what enters, in what
              order, from where, and how much is staggered. Sequence cannot be measured
              from a screenshot — the register gives you tempo and easing and stops
              there — so this is your decision, and without it every section fades in
              identically.",
  "treatments": [{"name": "...", "where": "...", "how": "exact classes or CSS"}]
}

All nine colour tokens are required. Values must be oklch.

Font names must be families that actually exist on Google Fonts, spelled exactly as
Google spells them — they are loaded by name and a typo is a build failure. In
`type_steps.classes` refer to them only as `font-display`, `font-body` or `font-mono`;
never write a family name into a class.

Tailwind classes must be real Tailwind v4 utilities."""

_JSON = re.compile(r"\{.*\}", re.DOTALL)



COMPOSE_SYSTEM = """You lay out a whole page. Not one section — the page, as a sequence.

You are given the sitemap in order, the design system already adopted, and screenshots of
the source page this site takes its structure from. The FIRST screenshot is that whole
page, tiled into columns, read top-to-bottom then left-to-right.

The problem you exist to solve, stated plainly: every section of this page is built by a
separate agent that cannot see any other section. Each one, left to decide its own shape,
picks the same safe shape — a centred column, a heading, a grid of equal cards. Ten good
sections in identical containers is a template. Rhythm is the thing none of them can
decide alone, so you decide it here, once, for all of them.

Look at what the source actually does across its length. Where does it go edge to edge and
where does it pull in? Where does the ground change? Which sections are dense and which
are almost empty? Where does it put a single large object and where a repeated small one?
That alternation is the evidence. Reproduce its RHYTHM — not its colours, not its brand.

For every section in the sitemap, decide:

  ground     "page" or "muted". The page ground is the default and should stay the
             majority. A muted band is a punctuation mark: it separates what is around
             it, and two adjacent muted sections merge into one grey block that neither
             builder can see happening. Never place two together.

  width      "contained" — the standard column, for type-led sections.
             "wide" — wider than the column, still inset. For grids and panels that
             need room.
             "full-bleed" — edge to edge. For a section carrying one large object, a
             band of colour, or a product panel meant to dominate. Use it deliberately
             and not more than a few times: everything full-bleed is as uniform as
             nothing full-bleed.

  archetype  the section's shape, in two or three words, from what the source shows:
             "split-with-panel", "centred-band", "asymmetric-grid", "full-bleed-panel",
             "stacked-editorial", "tight-logo-row", "large-numbers-row",
             "quote-with-portrait", "stepped-list". Invent one if the source shows a
             shape these do not name.

  contrast   one sentence: what makes this section look different from the section
             directly above it. If you cannot name a difference, the layout is wrong —
             change the width, the ground, or the archetype until you can.

  treatments the NAMES of the design system's treatments this section may use, from the
             list given below. Most sections get one, several get none. A treatment
             applied everywhere stops being a treatment and becomes the background: the
             last build put a gradient in six sections out of ten and the page read as
             busy rather than designed. Spend each one where it does the most work.

  signature  exactly ONE section in the whole page sets this true — the section that
             carries the design system's signature element at full strength. Every other
             section leaves it alone. This is the "spend your boldness in one place"
             rule, and it is the difference between a page with a memorable element and
             a page with a motif repeated until it is wallpaper.

Vary consecutively. Two sections in a row with the same width AND the same archetype is
the failure this pass exists to prevent.

JSON only, no prose, no code fence:

{ "sections": { "<section id>": { "ground": "...", "width": "...",
                                  "archetype": "...", "contrast": "...",
                                  "treatments": ["name", ...],
                                  "signature": false } },
  "rhythm": "two sentences on how the page paces itself top to bottom" }"""

class DesignDirector(Agent):
    name = "design_director"
    tier = Tier.TOP          # this agent's ceiling is the product's ceiling
    max_tokens = 12000

    def compose(self, bb: Blackboard, *, shots: list[str] | None = None,
                observed: str = "") -> tuple[dict, str, object]:
        """Decide the shape of every section, in one call, seeing the whole page.

        Deliberately separate from `direct`. A direction is chosen by the user at
        a gate and may be re-rolled; composition follows from whichever direction
        won and from the sitemap, neither of which exists when the directions are
        proposed.
        """
        order = sorted(bb.sections, key=lambda s: s.order)
        sitemap = "\n".join(
            f"  {i + 1}. {s.id}" for i, s in enumerate(order)
        )
        parts = [
            context_block(bb),
            f"<sitemap>\nThe page, in order:\n{sitemap}\n</sitemap>",
        ]
        if bb.design_system is not None:
            ts = "\n".join(f"  {t.name} — {t.where}"
                           for t in bb.design_system.treatments) or "  (none)"
            parts.append(
                "<design_system>\nAlready adopted and not yours to change here.\n"
                f"SIGNATURE: {bb.design_system.signature}\n"
                f"{bb.design_system.atmosphere}\n\n"
                f"TREATMENTS available to allocate, by name:\n{ts}\n"
                "</design_system>"
            )
        if observed:
            parts.append(observed)
        if shots:
            parts.append(
                "<source_page>\nThe first image is the whole source page tiled into "
                "columns; the rest are individual sections at full size. This is the "
                "page whose rhythm you are reproducing.\n</source_page>"
            )
        res = self.call(system=COMPOSE_SYSTEM, user="\n\n".join(parts), images=shots)
        m = _JSON.search(res.text)
        if not m:
            raise ValueError("design director returned no JSON for composition")
        d = first_object(m.group(0), what="composition reply")
        return d.get("sections") or {}, str(d.get("rhythm") or ""), res

    def direct(
        self, bb: Blackboard, *, sources: str = "",
        avoid: list[DesignSystem] | None = None,
        shots: list[str] | None = None,
    ) -> tuple[DesignSystem, str, object]:
        """Propose a direction. `avoid` forces a genuinely different one.

        Measured: three runs on identical inputs produced byte-identical design
        systems — same fonts, same oklch values to three decimals, same signature.
        That is good for replayability and useless at the approval gate, where a
        user who dislikes the direction needs a real alternative rather than the
        same answer again.

        Re-rolling cannot supply one, because nothing about the inputs changed.
        Divergence has to be instructed, so a rejected direction is passed back in
        and ruled out — the branch/replace split Superdesign uses, where branch is
        for alternatives and replace is for refining the chosen one.
        """
        parts = [context_block(bb)]
        if sources.strip():
            parts.append(
                "<sources>\nStructure and section inventory extracted from the reference "
                "sites.\n"
                f"{sources.strip()}\n</sources>"
            )
        if shots:
            # The screenshots of the WINNING source. Until these were passed,
            # nothing in this pipeline had ever seen a source site: this agent
            # decided a visual direction from a word count and an image count,
            # which is why four different briefs produced four pages with the
            # same container and the same section rhythm in different colours.
            parts.append(
                "<winning_source>\nThe screenshots below are the source that WON for "
                "this brief — the page whose structure and pacing this site is being "
                "built from. Look at them.\n\n"
                "The FIRST image is the whole page: its sections tiled into columns, "
                "read top-to-bottom then left-to-right. It is there for pacing — how "
                "many sections there are, which are dense and which breathe, where "
                "imagery falls. The images after it are individual sections at full "
                "size, for detail.\n\n"
                "Design with them in mind. What makes that page work — how it uses "
                "width, where it puts weight, how dense or sparse it is, how one "
                "section differs from the next — is the evidence you are deciding "
                "from. You are not required to depart from it, and a direction that "
                "ignores it is a direction built from nothing.\n\n"
                "Where you do depart, say so in `revised` and say why this subject "
                "needs something the winner does not do.\n</winning_source>"
            )
        if avoid:
            rejected = "\n\n".join(
                f"REJECTED DIRECTION {i}:\n  signature: {a.signature}\n"
                f"  atmosphere: {a.atmosphere}\n"
                f"  type: {a.font_display} / {a.font_body}\n"
                f"  ground: {next(c.value for c in a.colors if c.token == 'background')}\n"
                f"  primary: {next(c.value for c in a.colors if c.token == 'primary')}"
                for i, a in enumerate(avoid, 1)
            )
            parts.append(
                "<already_rejected>\n"
                "The user has seen the direction(s) below and asked for something else. "
                "Do not repeat them, and do not produce a variation of them.\n\n"
                f"{rejected}\n\n"
                "Change the ARGUMENT, not the adjectives. The rejected direction chose "
                "one reading of the subject; find a different true thing about it and "
                "build from that instead. A new signature, a different type register, and "
                "a ground that is not a neighbour of the rejected one. Say in `revised` "
                "what you changed the direction TO, and why it is a different idea rather "
                "than the same idea restyled.\n</already_rejected>"
            )

        res = self.call(system=SYSTEM, user="\n\n".join(parts), images=shots)

        m = _JSON.search(res.text)
        if not m:
            raise ValueError(f"design director returned no JSON:\n{res.text[:400]}")
        payload = first_object(m.group(0), what="design director reply")
        revised = payload.pop("revised", "")
        ds = DesignSystem.model_validate(payload)
        ds = self._resolve_fonts(ds)
        ds = self._repair_palette(ds, sources=sources, bb=bb)
        return ds, revised, res

    REPALETTE = """Your palette fails a check that is arithmetic, not taste.

Fix ONLY what is listed. Keep the atmosphere, the signature, the type and every other
decision exactly as they are — this is a correction, not a new direction. Adjust the
lightness or chroma of the named colours by the smallest amount that clears each floor,
and keep their names and roles.

JSON only: {"colors": [{"token": "...", "name": "...", "value": "oklch(L C H)",
                        "role": "..."}]}
Return the COMPLETE list of nine, including the ones you did not change."""

    def _repair_palette(self, ds: DesignSystem, *, sources: str = "",
                        bb=None, attempts: int = 2) -> DesignSystem:
        """Send measurable palette failures back to be fixed.

        Not a rejection of the direction — the atmosphere, signature and type are
        kept. Only the numbers move, and only far enough to clear the floor.
        """
        for _ in range(attempts):
            findings = check_palette(ds)
            if not findings:
                return ds
            res = self.call(
                system=self.REPALETTE,
                user=(f"<palette>\n"
                      + "\n".join(f"{c.token}: {c.name} — {c.value}" for c in ds.colors)
                      + f"\n</palette>\n\n<failures>\n{palette_report(findings)}\n"
                        "</failures>"),
            )
            m = _JSON.search(res.text)
            if not m:
                break
            try:
                fixed = first_object(m.group(0), what="design director reply")["colors"]
                ds.colors = [type(ds.colors[0]).model_validate(c) for c in fixed]
            except Exception:
                break
        return ds

    SUBSTITUTE = """You picked a typeface that Google Fonts does not serve. Replace it.

Pick the substitute that best preserves the design intent you already described. You may
only choose from the alternatives offered — they are the closest families Google actually
serves.

JSON only: {"replacements": {"<unavailable family>": "<chosen alternative>"}}"""

    def _resolve_fonts(self, ds: DesignSystem, attempts: int = 2) -> DesignSystem:
        """Swap any family Google does not serve for one it does.

        A design system naming an unavailable face fails at build time inside
        layout.tsx — a file no section owns, so the repairer cannot reach it. It
        is cheaper and far clearer to catch it here.
        """
        for _ in range(attempts):
            bad = validate_fonts(ds)
            if not bad:
                return ds
            offer = "\n".join(
                f"- {name!r} is unavailable. Alternatives: "
                + (", ".join(near) if near else "(no close match — pick any suitable family)")
                for name, near in bad.items()
            )
            res = self.call(
                system=self.SUBSTITUTE,
                user=(f"<intent>\n{ds.atmosphere}\n\nSignature: {ds.signature}\n</intent>\n\n"
                      f"<unavailable>\n{offer}\n</unavailable>"),
            )
            m = _JSON.search(res.text)
            if not m:
                break
            repl = first_object(m.group(0), what="design director reply").get("replacements", {})
            for field in ("font_display", "font_body", "font_mono"):
                cur = getattr(ds, field)
                if cur in repl:
                    setattr(ds, field, repl[cur])
        # Last resort: drop an unavailable mono rather than fail the build.
        if validate_fonts(ds) and ds.font_mono and ds.font_mono in validate_fonts(ds):
            ds.font_mono = None
        return ds

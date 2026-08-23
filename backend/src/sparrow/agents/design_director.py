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
from sparrow.render.tokens import validate_fonts

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
subject. Everything around it stays quiet and disciplined. Spend your boldness in one
place; cut any decoration that does not serve the brief.

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

## Work in two passes

FIRST, plan: atmosphere, signature, palette, type, spacing, motion.

THEN, before you commit, run the uniqueness test on your own plan. Work through what you
would produce for a DIFFERENT brief in the same category. Wherever you would arrive
somewhere similar, that part is a default rather than a choice — revise it, and say in
`revised` what you changed and why.

Only output the plan you arrive at after that pass.

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
  "container": "max-w-6xl px-6",
  "grid_gap": "gap-8",
  "inline_gap": "gap-3",
  "stack_tight": "space-y-4",
  "stack_loose": "space-y-8",
  "radius_base": "0.5rem", "radius_card": "rounded-lg", "radius_input": "rounded-md",
  "radius_full_allowed": "what may legitimately be fully round",
  "shadow_rest": "shadow-sm", "shadow_hover": "shadow-md",
  "imagery_treatment": "how product imagery is presented",
  "motion": "what moves, how far, how long"
}

All nine colour tokens are required. Values must be oklch.

Font names must be families that actually exist on Google Fonts, spelled exactly as
Google spells them — they are loaded by name and a typo is a build failure. In
`type_steps.classes` refer to them only as `font-display`, `font-body` or `font-mono`;
never write a family name into a class.

Tailwind classes must be real Tailwind v4 utilities."""

_JSON = re.compile(r"\{.*\}", re.DOTALL)


class DesignDirector(Agent):
    name = "design_director"
    tier = Tier.TOP          # this agent's ceiling is the product's ceiling
    max_tokens = 12000

    def direct(
        self, bb: Blackboard, *, sources: str = "", avoid: list[DesignSystem] | None = None
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
                "sites. Use these for what this category's pages CONTAIN. Do not adopt "
                "their look — the visual direction is yours to decide.\n"
                f"{sources.strip()}\n</sources>"
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

        res = self.call(system=SYSTEM, user="\n\n".join(parts))

        m = _JSON.search(res.text)
        if not m:
            raise ValueError(f"design director returned no JSON:\n{res.text[:400]}")
        payload = json.loads(m.group(0))
        revised = payload.pop("revised", "")
        ds = DesignSystem.model_validate(payload)
        return self._resolve_fonts(ds), revised, res

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
            repl = json.loads(m.group(0)).get("replacements", {})
            for field in ("font_display", "font_body", "font_mono"):
                cur = getattr(ds, field)
                if cur in repl:
                    setattr(ds, field, repl[cur])
        # Last resort: drop an unavailable mono rather than fail the build.
        if validate_fonts(ds) and ds.font_mono and ds.font_mono in validate_fonts(ds):
            ds.font_mono = None
        return ds

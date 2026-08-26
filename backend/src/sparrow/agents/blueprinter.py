"""The blueprinter.

Writes a section blueprint from what the ranked sources actually do, replacing
the last hand-written link in the chain.

A blueprint is a STRUCTURAL spec: what elements this section carries, in what
hierarchy, at what density. It is never aesthetics — palette, type and spacing
belong to `design_system`, and a blueprint that reaches into them takes the
builder's composition freedom away as well (`AGENT-RESEARCH.md` §12).

It writes from three things: the ranked winner's measurements, the `adopt` items
the ranker extracted, and the brief. The measurements matter — a blueprint that
says "a few features" produces a different page from one that says "six, in a
3-column grid, three lines of body each", and the second is what a real source
was observed doing.
"""

from __future__ import annotations

import json
import re

from sparrow.agents.base import Agent
from sparrow.blackboard.schema import Blueprint, Brief
from sparrow.providers import Tier

SYSTEM = """You write the structural spec for ONE section of a landing page, from
measurements of how real sites in this category build that section.

You are describing STRUCTURE, not looks. Say what elements exist, how many, in what
hierarchy, at what density, and how they reflow on mobile. Never mention colour,
typeface, spacing values, shadows or radius — those are decided elsewhere, and a
blueprint that names them removes the builder's judgement as well as the designer's.

USE THE COMPONENT VOCABULARY THE SOURCES USE. The register counts what this category
actually builds with — tabs, accordions, pill rows, code blocks, stat numbers, inline
diagrams. If a component appears across the sources and suits this section's job, ask for
it by name in `structure`. A blueprint that only ever specifies "cards with an icon, a
title and two lines of body" produces a page of identical cards, which is what a templated
site looks like.

Do not reach for a component the sources do not use, and do not add one for variety alone —
it has to do the section's job better than plain type would.

Ground every number in the evidence. "Several features" is a guess; "six features in a
3-column grid, each with an icon, a title and two to three lines of body" is what a real
page was measured doing. Where the evidence is thin, say what the section needs for THIS
brief rather than inventing a measurement.

Carry the ranked `adopt` items into the structure — they are the reason this source won.

A structural device only earns its place if it encodes something true. Numbered markers
(01 / 02 / 03) belong only where the content genuinely is a sequence. Say so explicitly
when you use one, and leave it out otherwise.

`slots` and `assets` are different things and go in different lists.

SLOTS are the copy the builder writes: eyebrow, headline, body, cta_label, features[],
question, answer. Every section has slots — a hero with none is a hero with no words.

An asset is not the only way to show a product. A section can also be built from composed
markup, inline SVG, a CSS-drawn panel, or an interactive component — and for content that
is inherently text, like code, logs, diffs, configuration or tabular data, markup carries
exact values that an image can only approximate. Ask for an asset when the section needs a
picture of something; describe the alternative in `structure` when it does not. The
register says which of these the category actually uses.

ASSETS are imagery someone must produce. Describe each one well enough to act on:
`product_image` is not a brief; "one 16:9 product capture showing the review packet with
its checkpoint state" is. A section that needs no imagery gets an empty list, and that is
a normal answer.

JSON only, no prose, no code fence:

{
  "purpose": "one sentence — what this section is for in this specific page",
  "slots": ["copy slots, lower_snake_case; suffix [] for repeated ones"],
  "assets": ["one sentence per image, describing what it must show"],
  "structure": "3-5 sentences. Layout, counts, hierarchy, mobile reflow, and what this
                section must NOT contain so it does not duplicate its neighbours."
}"""

_JSON = re.compile(r"\{.*\}", re.DOTALL)


class Blueprinter(Agent):
    name = "blueprinter"
    tier = Tier.CHEAP        # structure from evidence — no aesthetic judgement needed
    max_tokens = 3000

    def write(
        self,
        brief: Brief,
        section_type: str,
        ranking: dict,
        candidates: list,
        neighbours: list[str],
        vocabulary: dict | None = None,
    ) -> tuple[Blueprint, object]:
        winner = ranking.get("winner")
        won = [c for c in candidates if c.site == winner] or candidates
        others = [c for c in candidates if c.site != winner]

        evidence = ["WINNER — the structure to adapt:"]
        evidence += [f"  {c.line()}" for c in won]
        if others:
            evidence.append("")
            evidence.append("OTHER SOURCES — for range, not to copy:")
            evidence += [f"  {c.line()}" for c in others]

        adopt = "\n".join(f"  - {a}" for a in ranking.get("adopt", [])) or "  (none recorded)"

        # The counted component census. The instruction to use the sources'
        # vocabulary was already in the system prompt; the COUNTS were measured
        # by the scout, stored on the extract, and never rendered anywhere —
        # `Components.used()` had no caller at all. So the model was told to
        # match a vocabulary it was never shown, and defaulted to icon-title-body
        # cards every time. Measured on real sources: kiro.dev 17 accordions and
        # 62 inline SVGs, linear.app 8 pill rows, 11 code blocks, 183 SVGs.
        counted = ""
        for site, comps in (vocabulary or {}).items():
            used = comps.used() if hasattr(comps, "used") else []
            if used:
                counted += f"  {site}: {', '.join(used)}\n"

        user = "\n\n".join(x for x in [
            f"<brief>\nOffering: {brief.offering}\nAudience: {brief.audience}\n"
            f"Tone: {brief.tone}\nPrimary action: {brief.primary_action}\n</brief>",
            f"<section_type>{section_type}</section_type>",
            f"<why_this_source_won>\n{ranking.get('why', '')}\n</why_this_source_won>",
            (f"<counted_vocabulary>\nComponents counted on the sources, with how many "
             f"of each. This is what this category actually builds pages out of — ask "
             f"for one by name where it does this section's job better than plain type "
             f"would.\n{counted}</counted_vocabulary>") if counted else "",
            f"<adopt>\n{adopt}\n</adopt>",
            "<evidence>\n" + "\n".join(evidence) + "\n</evidence>",
            f"<neighbours>\nThis section sits in a page of: {', '.join(neighbours)}.\n"
            "Do not duplicate what an adjacent section already does.\n</neighbours>",
        ] if x)

        res = self.call(system=SYSTEM, user=user)
        m = _JSON.search(res.text)
        if not m:
            raise ValueError(f"blueprinter returned no JSON for {section_type}")
        d = json.loads(m.group(0))
        return (
            Blueprint(
                id=section_type,
                purpose=d["purpose"].strip(),
                slots=[str(s).strip() for s in d.get("slots", [])],
                assets=[" ".join(str(a).split()) for a in d.get("assets", [])],
                structure=" ".join(d["structure"].split()),
            ),
            res,
        )


def to_markdown(bp: Blueprint, component: str) -> str:
    return (
        f"# Blueprint: {bp.id}\n"
        f"**File:** `src/components/sections/{component}.tsx`\n\n"
        f"Purpose: {bp.purpose}\n\n"
        f"Slots: {' · '.join(bp.slots) or '—'}\n\n"
        + (f"Assets:\n" + "\n".join(f"- {a}" for a in bp.assets) + "\n\n" if bp.assets else "")
        + f"Structure: {bp.structure}\n"
    )

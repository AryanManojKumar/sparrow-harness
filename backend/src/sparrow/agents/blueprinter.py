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
from sparrow.parse import first_object

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

Repeated content is PARALLEL FLAT LISTS, never a nested path. Three feature cards each
with a title and a body are `feature_title[]` and `feature_body[]` — two slots, read
index by index. `features[].title` is not a slot name: nothing downstream can read it,
and a blueprint that uses one fails the run at the content stage.

An asset is not the only way to show a product. A section can also be built from composed
markup, inline SVG, a CSS-drawn panel, or an interactive component — and for content that
is inherently text, like code, logs, diffs, configuration or tabular data, markup carries
exact values that an image can only approximate. Ask for an asset when the section needs a
picture of something; describe the alternative in `structure` when it does not. The
register says which of these the category actually uses.

ASSETS are imagery someone must produce. Describe each one well enough to act on:
`product_image` is not a brief; "one 16:9 product capture showing the review packet with
its checkpoint state" is. A section that needs no imagery gets an empty list, and that is
a normal answer for ONE section — but read `<imagery_density>` before you give it. That
number is what these sources actually carry. A page whose sections each separately decided
they needed nothing lands nowhere near it, and reads as a stack of text blocks no matter
how good the copy is. If this section is one that in the sources shows something, say what
it shows.

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
    # Was CHEAP, on the grounds that structure from evidence needs no aesthetic
    # judgement. It does. This is the agent that decides whether a section shows
    # a product at all, and on fernbank it answered "no imagery" for eight of
    # nine sections against sources carrying twelve large images a page — a
    # decision no later stage can reverse, because the builder is then told the
    # section has none. It also now reads a screenshot, which the cheap tier is
    # weakest at.
    tier = Tier.MID
    max_tokens = 3000

    def write(
        self,
        brief: Brief,
        section_type: str,
        ranking: dict,
        candidates: list,
        neighbours: list[str],
        vocabulary: dict | None = None,
        shot: str | None = None,
        imagery: str = "",
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
            (f"<imagery_density>\n{imagery}\n</imagery_density>") if imagery else "",
            f"<adopt>\n{adopt}\n</adopt>",
            "<evidence>\n" + "\n".join(evidence) + "\n</evidence>",
            f"<neighbours>\nThis section sits in a page of: {', '.join(neighbours)}.\n"
            "Do not duplicate what an adjacent section already does.\n</neighbours>",
        ] if x)

        # The winning section's own screenshot. Everything else here is a count,
        # and `Candidate.line()` says why that is not enough: a hero reduced to
        # "3 img · 4 btn" carries nothing a model can reproduce a hero from.
        # 6398b98 gave the shot to the design director and the builder and
        # stopped there — leaving the agent that decides what is ON the page as
        # the only one working blind.
        res = self.call(system=SYSTEM, user=user,
                        images=[shot] if shot else None)
        m = _JSON.search(res.text)
        if not m:
            raise ValueError(f"blueprinter returned no JSON for {section_type}")
        d = first_object(m.group(0), what="blueprinter reply")
        return (
            Blueprint(
                id=section_type,
                purpose=d["purpose"].strip(),
                slots=_flatten_slots(d.get("slots", [])),
                assets=[" ".join(str(a).split()) for a in d.get("assets", [])],
                structure=" ".join(d["structure"].split()),
            ),
            res,
        )


def _flatten_slots(raw: list) -> list[str]:
    """`capability_modules[].title` -> `capability_modules_title[]`.

    The prompt asks for parallel flat lists and every blueprint but two obeyed;
    those two invented a nested path, and the content editor — which validates
    that the model filled every declared slot — failed the whole run on a name
    no part of this system can read. Normalising is not politeness to the model:
    the alternative is that one slot name costs a run its content, design and
    sources stages, all of which were already paid for.

    The bare parent (`capability_modules[]`) is dropped when it has children,
    because it is a container, not copy.
    """
    names = [str(s).strip() for s in raw if str(s).strip()]
    parents = {n.split("[].", 1)[0] for n in names if "[]." in n}
    out: list[str] = []
    for n in names:
        if "[]." in n:
            parent, child = n.split("[].", 1)
            n = f"{parent}_{child.replace('.', '_')}[]"
        elif n.rstrip("[]") in parents and n.endswith("[]"):
            continue
        if n not in out:
            out.append(n)
    return out


def to_markdown(bp: Blueprint, component: str) -> str:
    return (
        f"# Blueprint: {bp.id}\n"
        f"**File:** `src/components/sections/{component}.tsx`\n\n"
        f"Purpose: {bp.purpose}\n\n"
        f"Slots: {' · '.join(bp.slots) or '—'}\n\n"
        + (f"Assets:\n" + "\n".join(f"- {a}" for a in bp.assets) + "\n\n" if bp.assets else "")
        + f"Structure: {bp.structure}\n"
    )

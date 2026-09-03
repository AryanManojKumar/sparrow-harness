"""The content editor.

CLAUDE.md §2 names two differentiators. The asset gate covers one of them —
the user's real imagery. This covers the other: their real words.

WHAT IT REPLACES

Copy is written by the builder today, inline with the code, from one line of
instruction (`builder.py`: "Write real copy for this specific product. No lorem
ipsum."). That produces prose, but every claim in it is invented, and nothing
records which claims those were.

The only user words that reach a page today arrive through the hard-constraint
list, and they arrive VERBATIM, because §4 is right that a constraint must never
be summarised or rewritten. On the ide run, the constraints

    - we work great with legacy code aswell and new code
    - we are opensource, released under apche 2.0

shipped as hero body copy with "aswell" and "apche" intact. So the system has
exactly two modes for copy — invented, or pasted raw — and nothing in between.
The missing middle is the differentiator: take the user's real material and edit
it into the slot it belongs in.

WHY IT ASKS ABOUT FACTS AND NOT ABOUT SLOTS

The obvious design is a form: one field per slot. The ide run has 8 sections and
39 slots. Nobody fills 39 fields, and §11 says so in advance — "a business owner
who won't write an About page also won't fill in twelve prompts". §8 caps the
whole run at three gates for the same reason.

So this agent drafts EVERY slot, and then asks about almost none of them. The
question worth interrupting someone for is not "what should the eyebrow say" —
the model can write an eyebrow. It is the handful of places where the draft had
to assert something about their business that nothing in the brief supports: a
number, a customer name, a span of years, a named practice, a price. Those are
the lines that are either true and worth far more than anything a model can
write, or false and a liability on their site.

That distinction is the agent's whole job. A draft that invents nothing needs no
questions at all, and that is the common case for a nav or a footer.

PROVENANCE

Every slot carries where its words came from. `user_supplied` is what the user
wrote or confirmed, `drafted` is ours, `constraint` is their verbatim text placed
into a slot without alteration. The distinction is not bookkeeping: a restyle,
a rewrite pass, or a later tone change may freely redraft what we wrote, and must
never quietly rewrite what they did. `Provenance` on assets exists for the same
reason and was defined long before anything set it to more than one value; this
avoids repeating that.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from sparrow.parse import first_object

from sparrow.agents.base import Agent
from sparrow.blackboard.schema import Blueprint, Brief, Constraint
from sparrow.providers import Tier

_JSON = re.compile(r"\{.*\}", re.DOTALL)


class Source(StrEnum):
    """Where a slot's words came from. See the module docstring."""

    USER_SUPPLIED = "user_supplied"   # the user wrote or confirmed this
    DRAFTED = "drafted"               # we wrote it
    CONSTRAINT = "constraint"         # their verbatim words, placed, unaltered


@dataclass
class Ask:
    """One question worth interrupting a business owner for.

    Carries the draft, so the user edits a line rather than facing a blank box,
    and the invented claim by name, so they can see what they are being asked to
    confirm. `source_example` is what the winning source put in this slot —
    §6 says the content agent shows source snippets as reference for what is
    being requested, and it is also the honest answer to "why are you asking me
    this at all".
    """

    id: str
    section_id: str
    slot: str
    question: str            # plain language, answerable without seeing the site
    draft: str               # what we wrote, as the starting point to edit
    invented: str            # the specific claim the brief does not support
    source_example: str = ""


@dataclass
class Copy:
    """One section's drafted copy, plus the questions it raised."""

    section_id: str
    slots: dict[str, object] = field(default_factory=dict)     # str | list[str]
    provenance: dict[str, Source] = field(default_factory=dict)
    asks: list[Ask] = field(default_factory=list)

    def apply(self, ask_id: str, answer: str) -> None:
        """Record the user's answer to one ask, and mark the slot as theirs."""
        for a in self.asks:
            if a.id != ask_id:
                continue
            self.slots[a.slot] = answer
            self.provenance[a.slot] = Source.USER_SUPPLIED
            self.asks = [x for x in self.asks if x.id != ask_id]
            return
        raise KeyError(f"no open ask {ask_id!r} on section {self.section_id!r}")

    def unanswered(self) -> list[Ask]:
        return list(self.asks)


SYSTEM = """You write the copy for one section of a business website, and you report
every claim in it that you had to invent.

You are given the brief, the user's verbatim hard constraints, the section's purpose and
its named slots, and — where there is one — what the winning source site put in the same
slots.

## Write every slot

Fill every slot you are given. A slot named with `[]` repeats: return a list, and let the
source's count guide how many. Write for the audience and the register the brief names.

Copy that belongs to the interface — a button, a nav item, a field label — is not prose.
Match the length and directness of the source's equivalent. A call to action that reads
as a sentence is a defect, not a voice.

## The constraints are facts, not copy

The hard constraints are things the user told you are true about their business. Their
main job is to keep you honest: every line you write must be consistent with them, and
you may draw on what they say freely, in your own words.

MOST SLOTS SHOULD NOT CONTAIN A CONSTRAINT. A constraint is raw dictation, not written
copy — it has the register of a chat message, not of a page. Dropping one into a nav item,
a button, a metric or an eyebrow produces copy that reads as pasted, because it is.

Place a constraint verbatim ONLY when all of these hold:
- the slot is prose — a body, a subheading, a caption — not interface copy or a label
- the constraint reads as a finished sentence in that position
- saying it in your own words would weaken or soften the claim

At most one or two slots in an entire section should qualify, and often none.

When you do place one, reproduce it EXACTLY — same wording, same spelling, same
punctuation, even where it looks like an error. It is their claim about their own business
and it is not yours to correct. Report that slot's `source` as "constraint".

Everywhere else, report "drafted" — including where you wrote something a constraint
told you. A `source` of "constraint" is checked against the constraint text and downgraded
if it does not match character for character, so claiming it for a rephrasing gains you
nothing.

## Report what you invented

This is the part that matters.

After writing, go back over every line and find each place where you asserted something
about this business that the brief and the constraints do not support. Specifically:

- a number: a count, a percentage, a duration, a price, a team size, a founding year
- a named third party: a customer, a client, an employer, a partner, an integration
- a named person, a job title, or a quotation attributed to anyone
- a credential: a certification, an award, a compliance standard, a guarantee
- a specific practice or process presented as something this business actually does

For each one, raise an ask. The question must be answerable by a business owner who
cannot see the website and does not know what a slot is — ask about their business, not
about the page. "How many teams use it today?" is answerable. "What should the metric
eyebrow say?" is not.

DO NOT raise an ask for:
- anything the brief or a constraint already states
- a rephrasing of the offering or the audience in your own words
- interface copy: buttons, nav items, labels, form fields
- a description of what the product does that follows from the offering
- generic phrasing with no checkable content in it

An honest draft of a nav or a footer invents nothing and raises no asks. That is the
expected result, not a failure. A section that raises five asks is telling the user that
five of its lines are currently fiction, which is exactly what they need to know.

Respond with JSON only, no prose, no code fence:

{"slots": {"<slot>": "<copy>" or ["<copy>", ...]},
 "source": {"<slot>": "drafted" | "constraint"},
 "asks": [{"slot": "<slot>",
           "question": "<what you need to know, in plain language>",
           "invented": "<the exact claim you made up>"}]}

Every slot you were given must appear in "slots" and in "source"."""


class ContentEditor(Agent):
    """Drafts a section's copy and names what it had to invent.

    One call per section, not two. Drafting and auditing in separate calls means
    the auditor has to re-derive what the writer was thinking, and it doubles the
    cost of the cheapest stage in the run. The writer already knows which line it
    guessed at — the only thing needed is to make it say so.
    """

    name = "content-editor"
    # Copy is the half of the page a visitor actually reads, and unlike layout
    # there is no deterministic audit downstream that can catch a weak line.
    tier = Tier.MID
    max_tokens = 4000

    def write(
        self,
        brief: Brief,
        constraints: list[Constraint],
        blueprint: Blueprint,
        *,
        section_id: str,
        source_slots: dict[str, str] | None = None,
    ) -> Copy:
        parts = [
            "<brief>\n"
            + (f"Product name: {brief.product_name}\n" if brief.product_name else "")
            + f"Offering: {brief.offering}\n"
            f"Audience: {brief.audience}\n"
            f"Tone: {brief.tone}\n"
            f"Primary action: {brief.primary_action}\n"
            + (f"Secondary action: {brief.secondary_action}\n"
               if brief.secondary_action else "")
            + "</brief>",
        ]
        if constraints:
            parts.append(
                "<hard_constraints>\n"
                "The user's own words. Place them verbatim where they belong; never "
                "reword or correct them.\n"
                + "\n".join(f"- {c.text}" for c in constraints)
                + "\n</hard_constraints>"
            )
        parts.append(
            f"<section>\nid: {section_id}\npurpose: {blueprint.purpose}\n"
            f"slots: {', '.join(blueprint.slots)}\n</section>"
        )
        if source_slots:
            parts.append(
                "<source_example>\n"
                "What the winning source put in the same slots. For length, register "
                "and how much a slot is expected to carry — not to copy.\n"
                + "\n".join(f"{k}: {v}" for k, v in source_slots.items())
                + "\n</source_example>"
            )

        out = self.call(system=SYSTEM, user="\n\n".join(parts))
        return _parse(out.text, section_id, blueprint, source_slots or {},
                      constraints)


def _key(slot: str) -> str:
    """A slot name as the model will key it.

    Blueprints mark a repeating slot with a `[]` suffix — `nav_item[]`. That is a
    type marker for the builder, not part of the name, and the model keys it
    `nav_item` and returns a list, which is exactly right. Matching on the raw
    string instead rejected a correct nav response as an empty slot.
    """
    return slot[:-2] if slot.endswith("[]") else slot


def _parse(
    text: str,
    section_id: str,
    blueprint: Blueprint,
    source_slots: dict[str, str],
    constraints: list[Constraint] | None = None,
) -> Copy:
    m = _JSON.search(text)
    if not m:
        raise ValueError(f"content editor returned no JSON for {section_id!r}")
    data = first_object(m.group(0), what="content editor reply")

    slots = {_key(k): v for k, v in (data.get("slots") or {}).items()}
    declared = {_key(k): v for k, v in (data.get("source") or {}).items()}

    texts = [c.text.strip() for c in (constraints or [])]
    copy = Copy(section_id=section_id)
    for slot in blueprint.slots:
        # A slot the model skipped is a hole in the page, and a hole that reaches
        # the builder becomes an empty element the inspector then reports as a
        # visual defect two stages and several dollars later. Fail here instead.
        if _key(slot) not in slots:
            raise ValueError(
                f"content editor left slot {slot!r} empty on {section_id!r}"
            )
        copy.slots[slot] = slots[_key(slot)]
        raw = str(declared.get(_key(slot), Source.DRAFTED))
        # A "constraint" claim is VERIFIED, not believed. Measured on the ide
        # blueprints: the model marked a hero body as `constraint` while having
        # rewritten it into its own sentence, and marked a testimonial headline
        # as `constraint` after pasting an unrelated one there. Believing the
        # label would protect our own invented prose from ever being redrafted
        # — the one direction §4 cannot tolerate, since a constraint may be
        # superseded but never reworded. Match the text or it is ours.
        copy.provenance[slot] = (
            Source.CONSTRAINT
            if raw == Source.CONSTRAINT and _is_verbatim(copy.slots[slot], texts)
            else Source.DRAFTED
        )

    for i, a in enumerate(data.get("asks") or [], 1):
        slot = _match(a.get("slot", ""), copy.slots)
        # An ask against a slot that does not exist cannot be shown next to its
        # draft, and an ask with no question is a blank box with a heading.
        if slot is None or not a.get("question"):
            continue
        draft = copy.slots[slot]
        copy.asks.append(Ask(
            id=f"{section_id}-{i}",
            section_id=section_id,
            slot=slot,
            question=a["question"],
            draft=draft if isinstance(draft, str) else " · ".join(map(str, draft)),
            invented=a.get("invented", ""),
            source_example=source_slots.get(slot, ""),
        ))
    return copy


def _is_verbatim(value: object, texts: list[str]) -> bool:
    """Is this slot's copy one of the user's constraints, exactly as written?

    Exact after whitespace only. Nothing looser: "close enough to a constraint"
    is precisely the paraphrase §4 forbids, and a fuzzy match here would let a
    tidied-up version of the user's words inherit the label that stops anything
    tidying them.
    """
    if not isinstance(value, str):
        return False
    return " ".join(value.split()) in {" ".join(t.split()) for t in texts}


def _match(named: str, slots: dict[str, object]) -> str | None:
    """The declared slot an ask is against, or None if it names no real slot."""
    for slot in slots:
        if named == slot or _key(named) == _key(slot):
            return slot
    return None

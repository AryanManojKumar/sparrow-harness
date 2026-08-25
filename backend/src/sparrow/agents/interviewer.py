"""The interviewer.

Turns an open-ended sentence into a structured brief. CLAUDE.md §2: nothing is
generated until the brief exists, and a vague opening gets autocomplete chips
that expand into one rather than a blank form.

Two entry points, because the front of the funnel has two shapes:

`suggest` — a few words in the box. Cheap, fast, ranked completions. This is an
accelerator, not a step: it must never block typing, and a failure is silence.

`interview` — the submitted prompt, turned into a Brief. It fills what it can
infer and names what it had to assume, because an assumption the user can see and
correct is worth more than a question they have to answer before anything happens.

TONE IS THE STRONGEST FIELD. Measured in experiments/reactbits-01: changing that
one line moved the whole design from austere to kinetic and changed which motion
techniques the design agent would adopt. It is inferred carefully and always
surfaced for correction.
"""

from __future__ import annotations

import json
import re

from sparrow.agents.base import Agent
from sparrow.blackboard.schema import Brief, Constraint
from sparrow.providers import Tier

_JSON = re.compile(r"\{.*\}", re.DOTALL)

SUGGEST_SYSTEM = """You extend a half-written description of a business that needs a website.

You are NOT completing it into a finished prompt. You are drawing out the next thing worth
knowing, so the person keeps typing and the description gets more specific.

## Complete toward the FIRST gap that is still open

Four gaps, in order. Each has a bar. Work down the list, find the first one that has not
cleared its bar, and aim there.

1. OFFERING — what the business actually does.
   CLOSED once you know what it makes or provides and to whom it sells.
   "a bakery" is open. "a bakery that supplies sourdough to restaurants" is closed.

2. AUDIENCE — who buys, and what they already know, already tried, or fear.
   CLOSED once the buyer is named by role or situation, not just by market.
   "restaurants" is open. "head chefs let down by inconsistent delivery" is closed.

3. SPECIFICS — the thing a competitor could not copy into their own copy.
   CLOSED once there is at least one concrete, checkable fact: a number, a span of years,
   a refusal, a named practice.
   "high quality" is open. "the same three loaves for nine years" is closed.

4. PURPOSE — what the site is for: the action it should produce, and what a visitor must
   believe before taking it. Only reachable once 1–3 have cleared.

ONCE A GAP IS CLOSED, LEAVE IT. Do not ask for more detail on something already concrete —
which three loaves, how many restaurants exactly, what the pastries are called. That
deepens a gap instead of closing the next one, and it is how an interview turns into an
interrogation. If all four have cleared, aim at PURPOSE and offer completions about what
the site should make happen.

Do not skip ahead either. A page shape chosen before the business is understood is a
template, and the whole point is not to hand someone a template.

## How to write a completion

Continue their sentence in their own voice. Keep every fact they gave and add ONE more
clause — the next thing you would ask if you were sitting with them.

Prefer the concrete over the categorical. "…that supplies sourdough to about twenty
restaurants around Leeds" invites a correction; "…a food and beverage business" invites
nothing.

Never invent a fact as though they said it. Write the clause so an incorrect guess is
obviously a guess and cheap to fix.

## Output

`gap` is which of the four you aimed at, so the interface can show what it still needs.
`hint` is a short nudge shown under the rows — what to say next, in six words or so.

JSON only:
{"gap": "offering|audience|specifics|purpose",
 "hint": "six-word nudge for what to add next",
 "suggestions": [{"id": "kebab-slug", "text": "their sentence, extended by one clause",
                  "category": "2-3 words naming what the clause adds"}]}"""


INTERVIEW_SYSTEM = """You turn one sentence into a structured brief for a website build.

Nothing downstream runs until this exists, and every agent reads it, so it has to be
specific. Infer what you reasonably can and be honest about what you could not.

TONE is the field that matters most. It sets the visual direction more than any other
input — a brief saying "precise and technical, no hype" produces a restrained page, and
one saying "confident and kinetic" produces a different site from identical sources.
Write it as a real instruction about register and restraint, never as a list of adjectives.

CONSTRAINTS are the user's own words, kept verbatim. Extract only what they actually said
— a colour they rejected, a claim they must make, something they refuse to have on the
page. Do not invent constraints they did not state.

For anything you had to guess, say so in `assumed` in plain language, phrased so the
person can correct it in one line. "I assumed you sell to other businesses rather than
consumers" is correctable. "audience: B2B" is not.

JSON only:
{
  "category": "e.g. B2B SaaS landing page, local service site, portfolio",
  "offering": "what it does, concretely, in 1-2 sentences",
  "audience": "who buys it, and what they already know or fear",
  "tone": "register and restraint, as an instruction",
  "primary_action": "the one thing a visitor should do",
  "secondary_action": "or null",
  "constraints": ["verbatim, only what they actually said"],
  "assumed": ["one plain sentence per guess, correctable in one line"],
  "confidence": "high|low"
}"""


class Interviewer(Agent):
    name = "interviewer"
    tier = Tier.CHEAP
    max_tokens = 2000

    def suggest(self, partial: str, limit: int = 5) -> dict:
        """Autocomplete for the prompt box. Never raises — silence beats a stall.

        Returns the gap it aimed at alongside the rows, so the interface can show
        what the brief still needs rather than only what it could complete.
        """
        empty = {"gap": None, "hint": "", "suggestions": []}
        if len(partial.strip()) < 4:
            return empty
        try:
            res = self.call(system=SUGGEST_SYSTEM, user=partial.strip())
            m = _JSON.search(res.text)
            if not m:
                return empty
            d = json.loads(m.group(0))
        except Exception:
            return empty
        rows = [
            {"id": str(x.get("id", f"s{i}")), "text": str(x.get("text", "")).strip(),
             "category": str(x.get("category", "")).strip()}
            for i, x in enumerate(d.get("suggestions", []))
            if str(x.get("text", "")).strip()
        ][:limit]
        return {"gap": d.get("gap"), "hint": str(d.get("hint", "")).strip(),
                "suggestions": rows}


class BriefDraft(Agent):
    name = "interviewer"
    tier = Tier.MID          # this one decides the run's direction; do not economise
    max_tokens = 3000

    def interview(self, prompt: str) -> tuple[Brief, list[Constraint], list[str], str]:
        res = self.call(system=INTERVIEW_SYSTEM, user=prompt.strip())
        m = _JSON.search(res.text)
        if not m:
            raise ValueError("interviewer returned no JSON")
        d = json.loads(m.group(0))
        brief = Brief(
            category=d["category"].strip(),
            offering=" ".join(d["offering"].split()),
            audience=" ".join(d["audience"].split()),
            tone=" ".join(d["tone"].split()),
            primary_action=d["primary_action"].strip(),
            secondary_action=(d.get("secondary_action") or None),
        )
        constraints = [
            Constraint(id=f"c{i+1}", text=str(t).strip())
            for i, t in enumerate(d.get("constraints", [])) if str(t).strip()
        ]
        assumed = [str(a).strip() for a in d.get("assumed", []) if str(a).strip()]
        return brief, constraints, assumed, str(d.get("confidence", "low"))

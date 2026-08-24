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

SUGGEST_SYSTEM = """You complete a half-typed description of a website someone wants built.

Return up to five completions. Each is the FULL prompt they probably mean, written as they
would have written it — not a category label, not a question back.

Ground each in what a page of that kind actually contains, so the completion carries
information rather than adjectives: "a B2B SaaS platform — pricing table, logo wall,
integration grid" tells them what they are choosing; "a modern SaaS website" does not.

Stay close to what they typed. If they named an industry, keep it. If they named an
audience, keep it. Complete the sentence; do not replace it.

JSON only:
{"suggestions": [{"id": "kebab-slug", "text": "the full completed prompt",
                  "category": "2-3 word label"}]}"""

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

    def suggest(self, partial: str, limit: int = 5) -> list[dict]:
        """Autocomplete for the prompt box. Never raises — silence beats a stall."""
        if len(partial.strip()) < 4:
            return []
        try:
            res = self.call(system=SUGGEST_SYSTEM, user=partial.strip())
            m = _JSON.search(res.text)
            if not m:
                return []
            out = json.loads(m.group(0)).get("suggestions", [])
        except Exception:
            return []
        return [
            {"id": str(s.get("id", f"s{i}")), "text": str(s.get("text", "")).strip(),
             "category": str(s.get("category", "")).strip()}
            for i, s in enumerate(out) if str(s.get("text", "")).strip()
        ][:limit]


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

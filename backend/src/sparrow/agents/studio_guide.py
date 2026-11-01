"""Studio suggestions: what this owner might want to do next, as tappable chips.

The studio's user is not an engineer and will not open with a well-formed
request — §2's whole premise is that a blank prompt box is where these products
lose people. So the studio opens with options, and every option is a complete
request the agent can carry out on its own.

The options come from THIS site, not from a list: its brief, the gaps the
pipeline recorded (drafted copy where the owner never confirmed anything,
generated imagery standing in for real material), the pages that exist, and
what has already been changed in the studio. A fixed list would offer a
portfolio a pricing page.
"""

from __future__ import annotations

from sparrow.agents.base import Agent, context_block
from sparrow.blackboard.schema import Blackboard
from sparrow.parse import first_object
from sparrow.providers import Tier

KINDS = ("page", "content", "look", "motion", "fix")

INSTRUCTIONS = """\
You suggest next steps for the owner of a finished marketing website. They are \
not an engineer; they will tap one suggestion and an agent will carry it out on \
the site's code. Suggest what would make THIS site more useful to THIS audience, \
judged from the facts below — not a generic checklist.

Rules:
- Each suggestion must be doable by editing the site alone. Nothing that needs a \
file, a number, a name or a quote the owner has not given (the agent may not \
invent facts); if the idea needs owner facts, phrase it so the agent builds it \
with visible placeholders and say so in the label, e.g. "Pricing page (you fill \
in prices)".
- The site is a static export with no server and no form provider: nothing that \
submits, stores or sends data (forms, sign-ups, booking widgets) — it would look \
finished and do nothing.
- Do not repeat anything already changed in the studio, and do not propose what \
the page already has.
- Vary them: not five new pages.
- label: what the owner sees on the chip, at most 6 words, plain language.
- prompt: the full request the agent receives — specific to this site, naming \
the page or section, 1-3 sentences.
- kind: one of page, content, look, motion, fix.

Also write "complete": ONE comprehensive request that turns this into a finished \
multi-page site in a single pass — the request an owner taps when they want the \
whole thing done. It must:
- name every page the site should have, judged from its category, audience and \
offering AND from the broken links listed below (a footer that links to About, \
Contact and Privacy is asking for those pages); say in a clause what goes on each, \
drawn from facts the site already has;
- make every broken link work: build the missing page, or point the link at the \
right page or section (adding the section id it targets);
- keep Nav and Footer identical across pages and add the new pages to them;
- use visible placeholders for anything the owner has not given (names, prices, \
addresses, legal text) and never invent facts.
It is long by design: 8-15 sentences, plain imperative English.

Reply with JSON only:
{"complete": "...", "suggestions": [{"label": "...", "prompt": "...", "kind": "..."}]} \
with exactly 6 suggestions.
"""


class StudioGuide(Agent):
    name = "studio-guide"
    tier = Tier.MID
    max_tokens = 4000

    def suggest(self, bb: Blackboard, facts: str) -> tuple[str, list[dict]]:
        """(the complete-the-site request, six suggestions)."""
        out = self.call(system=INSTRUCTIONS + "\n\n" + context_block(bb), user=facts)
        body = first_object(out.text, what="suggestions")
        complete = str(body.get("complete") or "").strip()[:4000]
        rows = body.get("suggestions") or []
        clean = []
        for r in rows:
            label, prompt = str(r.get("label", "")).strip(), str(r.get("prompt", "")).strip()
            if not label or not prompt:
                continue
            kind = r.get("kind") if r.get("kind") in KINDS else "content"
            clean.append({"label": label[:60], "prompt": prompt[:800], "kind": kind})
        return complete, clean[:6]

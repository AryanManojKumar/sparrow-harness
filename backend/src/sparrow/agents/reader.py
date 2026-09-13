"""Reads the primary reference and says what it is doing.

Everything else the harness knows about a source is a COUNT. `12 large product
images`, `0.75 content share`, `3 accordions`, `tempo 300ms`. Counts are exact,
cheap and checkable, and they are a lossy projection: ramp.com and
elevenlabs.io/creative return nearly the same numbers and look nothing alike.
Worse, a count can only exist where someone anticipated it — the scout DETECTED
ramp's grain layer and filed it under motion as `noise__co5oY`, because no field
existed for surface treatment. It perceived more than it could say.

This agent is the open half of that. It looks at the page and describes it. No
schema decides in advance what is worth noticing, because the thing that makes a
page distinctive is precisely the thing nobody thought to add a field for.

WHAT IS CONSTRAINED HERE IS THE SHAPE OF AN ANSWER, NOT THE SPACE OF ANSWERS.
Every observation cites a band, so it can be checked against the screenshot;
names a mechanism, so a builder can act on it; and "nothing notable" is a
permitted answer, because a model asked what is remarkable will always find
something and invented distinctiveness reads exactly like the real kind.

Its output is a blackboard artifact, not a message (§3). The design director
already sees these screenshots; everything downstream of it does not. The
blueprinter sees one band, the composer sees none, the content editor sees
nothing at all. This is how what the source actually does reaches them.
"""

from __future__ import annotations

import re

from sparrow.agents.base import Agent
from sparrow.blackboard.schema import Blackboard
from sparrow.parse import first_object
from sparrow.providers import Tier

SYSTEM = """You are looking at one real website. Say what it is doing.

Not whether it is good. Not what it is for. What it DOES — the decisions someone
made that a reader feels and a count cannot see.

The rest of this harness measures this page already: how many images it carries,
how wide its content sits, how fast it animates, which components it repeats.
Those numbers exist and you do not need to restate them. You are here for what
they miss, and what they miss is most of why the page looks the way it does.

Nothing in this prompt tells you what to look for. That is deliberate. A list
would become the only things you find, and the interesting thing about any
particular page is the thing nobody thought to put on a list.

Three rules, and they are about how an answer is written, not about what may be
in one:

POINT AT SOMETHING. Every observation names the band it is in. If you cannot say
where you saw it, you did not see it.

SAY HOW IT IS DONE. "The hero feels spacious" is a reaction. "The headline sits
on its own line at roughly a third of the viewport height, with the product panel
starting below the fold" is a mechanism someone can build. If you cannot describe
the mechanism, leave it out.

NOTHING NOTABLE IS A REAL ANSWER. Many pages are ordinary and being ordinary is
not a defect. An empty list is better than a page's worth of invented character:
a fabricated observation is indistinguishable from a true one downstream, and it
will be built.

SOME OF WHAT IS ON SCREEN IS NOT THE PAGE. A cookie or consent dialog, a chat
launcher, a newsletter interstitial, a region banner — these arrive with the
visit, not with the design, and the first read of this page duly reported the
privacy panel as a feature and described how to build one. If a thing would
disappear the moment a reader dismissed it, it is not something this page does.
This is the one exclusion here, and it is about what is not the page rather than
about what may be noticed in it.

Between three and seven observations for a page. Fewer if that is what is there.

JSON only, no prose, no code fence:

{
  "observations": [
    {"where": "band 3",
     "what": "what is happening, in one sentence, observable from the image",
     "how": "the mechanism — what someone would build to get this"}
  ],
  "portrait": "two or three sentences: what this page is, as an object. What a
               person would remember about it an hour after closing the tab."
}"""

_JSON = re.compile(r"\{.*\}", re.DOTALL)


class Reader(Agent):
    name = "reader"
    # TOP, and not a place to save money. This agent's ceiling is how much of a
    # source the harness can see at all; everything downstream inherits whatever
    # it fails to notice, and no later stage can recover it.
    tier = Tier.TOP
    max_tokens = 3000

    def read(self, bb: Blackboard, *, site: str, images: list[str],
             counted: str = "") -> tuple[list[dict], str, object]:
        """Look at one page. Returns (observations, portrait, usage).

        `images` is the page's contact sheet first, then individual bands — the
        same order the design director gets them in, so "band 3" means the same
        thing to both.
        """
        parts = [
            f"<source>\nThis is {site}. The first image is the whole page, its "
            "sections tiled into columns, read top-to-bottom then left-to-right. "
            "The images after it are individual bands at full size, in page "
            "order — band 0 is the first.\n</source>",
        ]
        if counted.strip():
            parts.append(
                "<already_counted>\nThe harness has measured this much. Do not "
                "repeat it; it is here so you can spend your attention "
                f"elsewhere.\n{counted.strip()}\n</already_counted>"
            )
        res = self.call(system=SYSTEM, user="\n\n".join(parts), images=images)
        d = first_object(_JSON.search(res.text).group(0) if _JSON.search(res.text)
                         else res.text, what="reader reply")

        out: list[dict] = []
        for o in (d.get("observations") or [])[:8]:
            where = " ".join(str(o.get("where", "")).split())[:40]
            what = " ".join(str(o.get("what", "")).split())[:300]
            how = " ".join(str(o.get("how", "")).split())[:400]
            # An observation with no mechanism is a reaction, and a reaction
            # cannot be built. Dropped here rather than passed on, because
            # downstream has no way to tell the two apart.
            if what and how:
                out.append({"where": where, "what": what, "how": how})
        return out, " ".join(str(d.get("portrait", "")).split())[:600], res


def to_block(reading: dict) -> str:
    """The reading, as agents downstream receive it.

    Labelled OBSERVED, next to the design brief's counted facts, because the two
    have different standing: a count is exact and a reading is one model looking
    once. An agent should be able to tell which is which.
    """
    obs = reading.get("observations") or []
    if not obs and not reading.get("portrait"):
        return ""
    lines = [
        "<observed_source>",
        f"One reading of {reading.get('site', 'the primary reference')} — what it "
        "does that a count cannot see. OBSERVED, not measured: this is a model "
        "looking at screenshots once, so it is evidence with a softer standing "
        "than the numbers beside it.",
        "",
    ]
    if reading.get("portrait"):
        lines += [f"  {reading['portrait']}", ""]
    for o in obs:
        lines.append(f"  [{o['where']}] {o['what']}")
        lines.append(f"      how: {o['how']}")
    lines.append("</observed_source>")
    return "\n".join(lines)

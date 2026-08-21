"""The inspector.

Looks at what was built and reports what is wrong. It cannot fix anything —
that boundary is enforced by capability, not by instruction: this agent is
never handed a write tool, so no prompt can talk it into editing.

Two rules shape it.

DETERMINISTIC FIRST. Console errors, failed requests, horizontal overflow and
contrast ratios are computed in `sparrow.capture.inspect_page` before this agent
is asked anything. They arrive as findings, not as questions. Contrast is
arithmetic; a vision model asked to eyeball it will guess.

SECTIONS, NOT PAGES. It reasons over per-section screenshots. A full-page
capture of a long landing page is resized to an illegible strip — the arithmetic
is in `SectionShot.image_tokens`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sparrow.agents.base import Agent, stable_system
from sparrow.blackboard.schema import Blackboard, Section
from sparrow.capture import PageReport
from sparrow.providers import Tier

SYSTEM = """You are the inspector for a website harness. You look at one built section
and report what is WRONG with it. You do not write code and you cannot edit anything.

You are given the brief, the design system the section was built to, and screenshots
of that section as it actually renders at each breakpoint.

REPORT ONLY DEFECTS YOU CAN SEE OR POINT AT:
- text that overflows, clips, wraps badly, or collides with another element
- elements that overlap, misalign, or break out of their container
- a layout that collapses or becomes unusable at a breakpoint
- content visibly longer or shorter than the layout assumed
- a stated hard constraint visibly violated
- an element that is invisible, empty, or obviously unstyled

DO NOT REPORT:
- taste. Not "could be more modern", not "spacing feels tight", not "consider a
  stronger hierarchy". You are not scoring design.
- ANYTHING THE SOURCE ALREADY ANSWERS. Which type step, colour token, font weight,
  radius, shadow or spacing value a element uses is read directly from the code by
  a separate deterministic audit that cannot be fooled. You are looking at a picture
  and you cannot tell text-4xl from text-5xl, or one grey from another. Every time
  you have guessed at one, you have been wrong. Do not mention the type scale, the
  palette, or the spacing scale at all.
- anything already listed under <deterministic_findings>. It has been measured.
  Do not restate it, and do not second-guess a computed contrast ratio by eye.
- speculation about code you cannot see.
- anything you would not be willing to point at with a finger.

Your entire value is what ONLY rendering reveals: things that overflow, collide,
clip, collapse, or come out empty. The code has already been checked; the picture
has not.

A section with no visible defects is a PASS, and passing is the common case. An
inspector that always finds something is an inspector nobody reads.

Respond with JSON only, no prose, no code fence:

{"defects": [{"severity": "high|medium|low", "what": "<what is wrong>",
              "where": "<which element or region, and at which breakpoint>"}]}

Empty list means the section passes."""

_JSON = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Defect:
    severity: str
    what: str
    where: str
    source: str  # "computed" or "vision"

    def __str__(self) -> str:
        mark = {"high": "!!", "medium": " !", "low": "  "}.get(self.severity, "  ")
        return f"{mark} [{self.source}] {self.what} — {self.where}"


class Inspector(Agent):
    name = "inspector"
    tier = Tier.MID
    max_tokens = 4000

    def inspect_section(
        self,
        bb: Blackboard,
        section: Section,
        shots: list,
        page_findings: list[Defect],
    ) -> tuple[list[Defect], object]:
        det = (
            "\n".join(f"- {d.what} ({d.where})" for d in page_findings)
            or "none — the deterministic pass found nothing on this page"
        )
        user = "\n\n".join([
            f"<section>\nid: {section.id}\nblueprint: {section.blueprint_id}\n</section>",
            f"<deterministic_findings>\n{det}\n</deterministic_findings>",
            "<screenshots>\n"
            + "\n".join(f"- {s.breakpoint} ({s.width}x{s.height})" for s in shots)
            + "\n</screenshots>",
        ])
        res = self.call(
            system=stable_system(SYSTEM, bb), user=user,
            images=[s.b64() for s in shots],
        )

        m = _JSON.search(res.text)
        if not m:
            return [], res
        try:
            payload = json.loads(m.group(0))
        except json.JSONDecodeError:
            return [], res
        return [
            Defect(
                str(d.get("severity", "medium")),
                str(d.get("what", "")).strip(),
                str(d.get("where", "")).strip(),
                "vision",
            )
            for d in payload.get("defects", [])
            if str(d.get("what", "")).strip()
        ], res


def deterministic_defects(reports: dict[str, PageReport]) -> list[Defect]:
    """Findings that needed no model at all."""
    out: list[Defect] = []
    for bp, r in reports.items():
        for e in r.console_errors:
            out.append(Defect("high", f"console error: {e}", bp, "computed"))
        for f in r.failed_requests:
            out.append(Defect("high", f"request failed: {f}", bp, "computed"))
        for o in r.horizontal_overflow:
            out.append(Defect("high", f"content overflows the viewport: {o}", bp, "computed"))
        for c in r.contrast_failures:
            out.append(Defect("medium", f"contrast {c}", bp, "computed"))
    return out

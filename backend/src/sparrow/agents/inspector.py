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

WHAT YOU ARE LOOKING AT: an element screenshot of ONE section, cropped out of the page.
The top and bottom edges are CROP BOUNDARIES, not clipping, not occlusion, and not a
navigation bar sitting on top of the content. Nothing from any other section is present in
this image — no header, no nav, no footer, no neighbouring section. If the content appears
to start or end abruptly at an edge, that is the crop, and it is not a defect.

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

Empty list means the section passes.

## Red flags

Each row is a thought that has actually produced a false report from this agent.

| Thought | Reality |
|---------|---------|
| "That heading looks like the hero display step" | You cannot tell text-4xl from text-5xl in a picture. You reported this once and were wrong — it was the h2 step. The source is checked separately. |
| "That grey looks too light against the background" | Contrast was measured to four significant figures before you were called. Your eye is not an instrument. |
| "I have looked at five sections and found nothing, I should find something" | Passing is the common case. An inspector that always finds something is one nobody reads. |
| "The spacing here feels tight" | Feelings are not defects. If you cannot point at it, it is not yours to report. |
| "This would look better as two columns" | You are not redesigning. Report what is broken, not what is different. |
| "The brief mentions X but this section has no X" | Sections divide the brief between them. The blueprint says what THIS one carries; what it omits, it omits deliberately. |
| "The deterministic pass missed this contrast issue, I should flag it" | If it is not in the findings, it passed. Do not relitigate arithmetic. |
| "This element might be misaligned" | Might is not a report. Either it visibly is, or you say nothing. |
| "A navigation bar is overlapping the top of this section" | There is no navigation bar in this image. You are looking at one section, cropped. The top edge is the crop. You reported this across four sections on one page and were wrong every time. |
| "The content is clipped at the top/bottom edge" | That is where the crop is. Clipping means content cut off INSIDE the section by a container, not content meeting the boundary of the picture. |"""

_JSON = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Defect:
    """A defect carries a routing code AND a human message, never one or the other.

    `code` is stable lower-kebab-case the orchestrator branches on — it decides
    whether this goes to the repairer, to the design director, or to the user as
    an escalation. `what` is what a person reads. CLAUDE.md §8 requires both.
    """

    severity: str
    code: str
    what: str
    where: str
    source: str  # "computed" or "vision"

    def __str__(self) -> str:
        mark = {"high": "!!", "medium": " !", "low": "  "}.get(self.severity, "  ")
        return f"{mark} [{self.source}:{self.code}] {self.what} — {self.where}"


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
        blueprint=None,
        already_disputed: list[str] | None = None,
    ) -> tuple[list[Defect], object]:
        det = (
            "\n".join(f"- {d.what} ({d.where})" for d in page_findings)
            or "none — the deterministic pass found nothing on this page"
        )
        user = "\n\n".join([
            f"<section>\nid: {section.id}\nblueprint: {section.blueprint_id}\n</section>",
            # Without the blueprint, "missing" is unanswerable. The inspector once
            # reported a CTA for lacking the brief's secondary action, when that
            # section's blueprint says in as many words: no secondary action.
            ("<blueprint>\nWhat this section is SUPPOSED to contain. Anything the "
             "blueprint excludes is not a defect — it is the design.\n"
             f"purpose: {blueprint.purpose}\nslots: {', '.join(blueprint.slots)}\n"
             f"structure: {blueprint.structure}\n</blueprint>")
            if blueprint is not None else
            "<blueprint>not available — do not report anything as missing</blueprint>",
            f"<deterministic_findings>\n{det}\n</deterministic_findings>",
            ("<already_disputed>\nThese were reported on an earlier pass and the "
             "builder rejected them with a reason. Do not report them again unless you "
             "can point at something new.\n"
             + "\n".join(f"- {d}" for d in already_disputed)
             + "\n</already_disputed>") if already_disputed else "",
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
                "visual-defect",
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
            out.append(Defect("high", "console-error", f"console error: {e}", bp, "computed"))
        for f in r.failed_requests:
            out.append(Defect("high", "request-failed", f"request failed: {f}", bp, "computed"))
        for o in r.horizontal_overflow:
            out.append(Defect("high", "viewport-overflow", f"content overflows the viewport: {o}", bp, "computed"))
        for c in r.contrast_failures:
            out.append(Defect("medium", "contrast-below-wcag", f"contrast {c}", bp, "computed"))
    return out

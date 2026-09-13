"""Deterministic palette checks.

A design system can be internally consistent and still produce a washed-out page.
The run that prompted this had four of nine colours above L=0.92, its two section
grounds 0.055 apart in lightness, and a maximum chroma of 0.17 — so the
alternation between sections was invisible and nothing on the page was saturated.
Every builder honoured it faithfully; the drift audit was clean; the inspector
found nothing. The palette was simply too pale, and no one was looking.

Separation is arithmetic, so it is checked rather than judged. OKLCH is
perceptually uniform, which is what makes a lightness threshold meaningful at all
— the same delta reads the same anywhere on the scale.

These are floors, not taste. A restrained palette is a legitimate choice; one
whose section grounds cannot be told apart is a defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sparrow.blackboard.schema import DesignSystem

_OKLCH = re.compile(r"oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)")

# Floors, each with a reason rather than a preference.
GROUND_SEPARATION = 0.07   # below this, alternating sections read as one block
BORDER_SEPARATION = 0.08   # below this, a hairline disappears into its ground
MIN_TEXT_SEPARATION = 0.40 # foreground vs its ground; roughly WCAG AA for body
SATURATED_CHROMA = 0.11    # at least one colour has to actually be a colour
MAX_NEAR_WHITE = 3         # of nine; more than this and every surface is the same


@dataclass
class Finding:
    code: str
    message: str


def parse(value: str) -> tuple[float, float, float]:
    m = _OKLCH.search(value)
    if not m:
        raise ValueError(f"not an oklch colour: {value!r}")
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def check(ds: DesignSystem) -> list[Finding]:
    by = {c.token: c for c in ds.colors}

    def L(token: str) -> float:
        return parse(by[token].value)[0]

    def C(token: str) -> float:
        return parse(by[token].value)[1]

    out: list[Finding] = []

    if {"background", "muted"} <= by.keys():
        d = abs(L("background") - L("muted"))
        if d < GROUND_SEPARATION:
            out.append(Finding(
                "grounds-too-close",
                f"background ({by['background'].name}, L={L('background'):.3f}) and muted "
                f"({by['muted'].name}, L={L('muted'):.3f}) differ by {d:.3f}. Below "
                f"{GROUND_SEPARATION}, alternating sections read as one long block and the "
                f"page loses its rhythm. Separate them by at least {GROUND_SEPARATION}.",
            ))

    if {"border", "background"} <= by.keys():
        d = abs(L("border") - L("background"))
        if d < BORDER_SEPARATION:
            out.append(Finding(
                "border-invisible",
                f"border ({by['border'].name}) is {d:.3f} from the page ground. A hairline "
                f"that close disappears, and a design leaning on hairlines instead of cards "
                f"then has no visible structure at all.",
            ))

    if {"foreground", "background"} <= by.keys():
        d = abs(L("foreground") - L("background"))
        if d < MIN_TEXT_SEPARATION:
            out.append(Finding(
                "text-too-faint",
                f"foreground and background differ by only {d:.3f} in lightness.",
            ))

    top = max(C(t) for t in by)
    if top < SATURATED_CHROMA:
        hue = max(by, key=lambda t: C(t))
        out.append(Finding(
            "no-saturated-colour",
            f"the most saturated colour in the palette is {by[hue].name} at C={top:.3f}. "
            f"Below {SATURATED_CHROMA} nothing on the page reads as a colour — it renders "
            f"as tinted grey, which is what 'washed out' means numerically. Give at least "
            f"the primary real chroma.",
        ))

    near_white = [t for t in by if L(t) > 0.92]
    if len(near_white) > MAX_NEAR_WHITE:
        out.append(Finding(
            "too-many-near-white",
            f"{len(near_white)} of {len(by)} colours sit above L=0.92 "
            f"({', '.join(by[t].name for t in near_white)}). Stacked near-white surfaces "
            f"cannot be distinguished from each other, so cards, grounds and fills all "
            f"merge.",
        ))

    return out


def report(findings: list[Finding]) -> str:
    if not findings:
        return "palette ok"
    return "\n".join(f"  [{f.code}] {f.message}" for f in findings)

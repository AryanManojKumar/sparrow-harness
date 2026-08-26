"""Deterministic drift audit.

Everything here is computed, never judged. It derives what is permitted from the
same `DesignSystem` the builder was given, so the audit cannot disagree with the
prompt — they read one source.

This runs before `inspector` ever opens a browser. A violation that a regex can
find is not worth a vision call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sparrow.blackboard.schema import DesignSystem

_PALETTES = (
    "white|black|slate|gray|grey|zinc|neutral|stone|red|orange|amber|yellow|lime|"
    "green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose"
)
LITERAL_COLOR = re.compile(
    rf"\b(?:text|bg|border|from|via|to|ring|fill|stroke|decoration|outline)-"
    rf"(?:{_PALETTES})(?:-\d{{2,3}})?\b"
)
FONT_WEIGHT = re.compile(r"\bfont-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)\b")
# Both of these also match arbitrary values, because a closed alternation cannot
# see the thing it most needs to catch. `ide-01` used shadow-[0_2px_0_0_oklch(
# 0.805_0.032_235)] eleven times against a design system declaring
# shadow-[0_1px_0_0_oklch(0.720_0.045_230)] — a different colour AND a different
# offset, invisible to the audit because it was not a named Tailwind step. That
# is the "tenth value at section six" §6 says the recorded decision exists to
# prevent. `permitted()` stores declared values verbatim, so arbitrary values
# compare correctly once they are matched at all.
TEXT_STEP = re.compile(
    r"\btext-(?:xs|sm|base|lg|xl|[2-9]xl)\b"
    # Only size-like arbitrary values. text-[#fff] is a colour, not a type step,
    # and belongs to the colour rule.
    r"|\btext-\[[^\]]*(?:rem|px|em|vw|vh|ch|clamp)[^\]]*\]"
)
SHADOW = re.compile(r"\bshadow-(?:2xl|xl|lg|md|sm|none|inner)\b|\bshadow-\[[^\]]*\]")
ROUNDED = re.compile(r"\brounded-(?:none|sm|md|lg|xl|2xl|3xl|full)\b")
# Captures the SIZE, and tolerates both the fractional steps Tailwind really has
# and the axis variants. `\bgap-\d+\b` matched "gap-2" inside "gap-2.5" and
# reported it as off-scale — on the ide-01 run that produced 31 findings, every
# one of them against `gap-2.5`, which is the exact string the design system
# declared as `inline_gap`. The builder had followed the spec perfectly and the
# audit called it drift 31 times.
GAP = re.compile(r"\bgap(?:-[xy])?-(\d+(?:\.\d+)?|px)\b")
BANNED_IMPORT = re.compile(r"""from\s+["']framer-motion["']""")

INLINE_STYLE_COLOR = re.compile(r"style=\{\{[^}]*(?:color|background)[^}]*\}\}")

_WEIGHT_NAMES = {
    100: "thin", 200: "extralight", 300: "light", 400: "normal",
    500: "medium", 600: "semibold", 700: "bold", 800: "extrabold", 900: "black",
}


@dataclass
class Finding:
    file: str
    line: int
    category: str
    detail: str


def _lines(p: Path) -> list[tuple[int, str]]:
    return list(enumerate(p.read_text().splitlines(), 1))


def permitted(ds: DesignSystem) -> dict[str, set[str]]:
    """What each off-scale category is allowed to contain, keyed by category.

    Two callers read this: the audit, which uses it to decide whether a utility
    is drift, and `steps._drift_defects`, which quotes it back to the fixer so a
    finding names its own remedy. Deriving it twice is how a check and its fix
    end up disagreeing about what the scale is — the schema docstring makes the
    same point about tokens and CSS.
    """
    # A declared value is often a responsive set — "gap-6 md:gap-8" is ONE
    # decision expressed as two utilities. Comparing whole strings against
    # individual classes flagged a builder that had followed the spec exactly.
    def utilities(*declared: str) -> set[str]:
        out: set[str] = set()
        for d in declared:
            for part in d.split():
                out.add(part.split(":")[-1])
        return out

    return {
        "off-scale-weight": {f"font-{_WEIGHT_NAMES[w]}" for w in ds.font_weights},
        "off-scale-type": {m.group(0) for st in ds.type_steps
                           for m in TEXT_STEP.finditer(st.classes)},
        "off-scale-shadow": utilities(ds.shadow_rest, ds.shadow_hover),
        "off-scale-radius": utilities(ds.radius_card, ds.radius_input) | {"rounded-full"},
        "off-scale-gap": utilities(ds.grid_gap, ds.inline_gap),
    }


def bare(utility: str) -> str:
    """Strip responsive/state variants without touching an arbitrary value.

    `md:shadow-[...]` is the same decision as `shadow-[...]`. Splitting on every
    colon would also cut Tailwind's typed arbitrary syntax, `shadow-[color:red]`,
    in half — so only the part before the bracket is considered.
    """
    head, sep, rest = utility.partition("[")
    return head.split(":")[-1] + sep + rest


def gap_size(utility: str) -> str:
    """"gap-x-2.5" -> "2.5". Both sides of the gap comparison go through this."""
    m = GAP.search(utility)
    return m.group(1) if m else utility


def audit_file(path: Path, ds: DesignSystem) -> list[Finding]:
    allow = permitted(ds)
    allowed_gap_sizes = {gap_size(g) for g in allow["off-scale-gap"]}

    out: list[Finding] = []
    name = path.name
    for n, line in _lines(path):
        for m in LITERAL_COLOR.finditer(line):
            out.append(Finding(name, n, "literal-color", m.group(0)))
        for m in FONT_WEIGHT.finditer(line):
            if bare(m.group(0)) not in allow["off-scale-weight"]:
                out.append(Finding(name, n, "off-scale-weight", m.group(0)))
        for m in TEXT_STEP.finditer(line):
            if bare(m.group(0)) not in allow["off-scale-type"]:
                out.append(Finding(name, n, "off-scale-type", m.group(0)))
        for m in SHADOW.finditer(line):
            if bare(m.group(0)) not in allow["off-scale-shadow"]:
                out.append(Finding(name, n, "off-scale-shadow", m.group(0)))
        for m in ROUNDED.finditer(line):
            if bare(m.group(0)) not in allow["off-scale-radius"]:
                out.append(Finding(name, n, "off-scale-radius", m.group(0)))
        for m in GAP.finditer(line):
            # Compared by size rather than by whole utility, so a declared
            # `gap-8` also permits `gap-x-8`: same decision, one axis of it.
            if m.group(1) not in allowed_gap_sizes:
                out.append(Finding(name, n, "off-scale-gap", m.group(0)))
        if BANNED_IMPORT.search(line):
            out.append(Finding(name, n, "banned-import", "framer-motion — use motion/react"))
        if INLINE_STYLE_COLOR.search(line):
            out.append(Finding(name, n, "inline-style-color", line.strip()[:60]))
    return out


def audit_dir(sections: Path, ds: DesignSystem) -> list[Finding]:
    out: list[Finding] = []
    for p in sorted(sections.glob("*.tsx")):
        out.extend(audit_file(p, ds))
    return out


def summarise(findings: list[Finding]) -> str:
    if not findings:
        return "clean — no drift"
    by: dict[str, int] = {}
    for f in findings:
        by[f.category] = by.get(f.category, 0) + 1
    head = ", ".join(f"{v}× {k}" for k, v in sorted(by.items(), key=lambda kv: -kv[1]))
    lines = [f"{len(findings)} findings: {head}", ""]
    lines += [f"  {f.file}:{f.line}  {f.category:20} {f.detail}" for f in findings]
    return "\n".join(lines)

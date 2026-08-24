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
TEXT_STEP = re.compile(r"\btext-(xs|sm|base|lg|xl|[2-9]xl)\b")
SHADOW = re.compile(r"\bshadow-(?:2xl|xl|lg|md|sm|none|inner)\b")
ROUNDED = re.compile(r"\brounded-(?:none|sm|md|lg|xl|2xl|3xl|full)\b")
GAP = re.compile(r"\bgap-\d+\b")
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


def audit_file(path: Path, ds: DesignSystem) -> list[Finding]:
    allowed_weights = {_WEIGHT_NAMES[w] for w in ds.font_weights}
    allowed_steps = {
        m.group(1)
        for st in ds.type_steps
        for m in TEXT_STEP.finditer(st.classes)
    }
    # A declared value is often a responsive set — "gap-6 md:gap-8" is ONE
    # decision expressed as two utilities. Comparing whole strings against
    # individual classes flagged a builder that had followed the spec exactly.
    def utilities(*declared: str) -> set[str]:
        out: set[str] = set()
        for d in declared:
            for part in d.split():
                out.add(part.split(":")[-1])
        return out

    allowed_shadows = utilities(ds.shadow_rest, ds.shadow_hover)
    allowed_rounded = utilities(ds.radius_card, ds.radius_input) | {"rounded-full"}
    allowed_gaps = utilities(ds.grid_gap, ds.inline_gap)

    out: list[Finding] = []
    name = path.name
    for n, line in _lines(path):
        for m in LITERAL_COLOR.finditer(line):
            out.append(Finding(name, n, "literal-color", m.group(0)))
        for m in FONT_WEIGHT.finditer(line):
            if m.group(1) not in allowed_weights:
                out.append(Finding(name, n, "off-scale-weight", m.group(0)))
        for m in TEXT_STEP.finditer(line):
            if m.group(1) not in allowed_steps:
                out.append(Finding(name, n, "off-scale-type", m.group(0)))
        for m in SHADOW.finditer(line):
            if m.group(0).split(":")[-1] not in allowed_shadows:
                out.append(Finding(name, n, "off-scale-shadow", m.group(0)))
        for m in ROUNDED.finditer(line):
            if m.group(0).split(":")[-1] not in allowed_rounded:
                out.append(Finding(name, n, "off-scale-radius", m.group(0)))
        for m in GAP.finditer(line):
            if m.group(0).split(":")[-1] not in allowed_gaps:
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

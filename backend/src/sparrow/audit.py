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
FONT_WEIGHT = re.compile(r"\bfont-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black|[1-9]00)\b")
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
        # Both spellings: the theme declares `--font-weight-<n>` for each
        # recorded weight, so `font-500` is as real as `font-medium`.
        "off-scale-weight": ({f"font-{_WEIGHT_NAMES[w]}" for w in ds.font_weights}
                             | {f"font-{w}" for w in ds.font_weights}),
        "off-scale-type": {m.group(0) for st in ds.type_steps
                           for m in TEXT_STEP.finditer(st.classes)},
        # The recorded SCALE plus the single defaults. A scale recorded from the
        # source's measured vocabulary permits the surfaces the source has;
        # nothing here widens on its own.
        "off-scale-shadow": utilities(ds.shadow_rest, ds.shadow_hover,
                                      *(getattr(ds, "shadow_scale", None) or [])),
        "off-scale-radius": utilities(ds.radius_card, ds.radius_input,
                                      *(getattr(ds, "radius_scale", None) or [])) | {"rounded-full"},
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


# An internal link to a path. The export is one page, so any href that starts
# with `/` and is not the page itself is a route that does not exist; Next
# prefetches it and the preview logs a 404 per link.
DEAD_ROUTE = re.compile(r"""href(?:=|:\s*)\{?["'](/(?!$|#|projects/)[^"'\s]*)["']""")


# A `url()` inside a class value. Turbopack resolves it as a module at build
# time; a basePath-prefixed path exists only at serve time, so the build fails —
# and because the previous export in out/ carried the same class, restoring the
# file did not recover it. Assets are placed with <img>/next/image at the base
# the builder is given, never through CSS.
CSS_URL = re.compile(r"""\[[^\]]*url\(""")


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
        if CSS_URL.search(line):
            out.append(Finding(name, n, "css-url-asset",
                               "url() inside a class value — Turbopack resolves it as a "
                               "module and the build fails; place the asset with <img> or "
                               "next/image at the given asset base instead"))
        for m in DEAD_ROUTE.finditer(line):
            out.append(Finding(name, n, "dead-route",
                               f"{m.group(1)} — no such route on a one-page export; "
                               "link to a section anchor (#<section id>) or #top"))
    return out


# A block that is boxed: a container className carrying a full border AND
# either a card fill or a shadow. `border-t`/`border-b` alone is a rule, not a
# box, and is deliberately not matched.
_BOXED = re.compile(
    r'className=\{?["`][^"`]*\bborder(?:-2|-\[[^\]]+\])?\b(?![-\w])[^"`]*'
    r'(?:\bbg-card\b|\bshadow-(?:sm|md|lg|xl|2xl|\[[^\]]+\]))'
)
_ANY_BLOCK = re.compile(r'<(?:div|section|article|li|figure|aside)\b')


def enclosure_of(path: Path) -> tuple[int, int]:
    """(boxed containers, all containers) in one section file — the code-side
    twin of the scout's per-band measurement, so the two are comparable."""
    src = path.read_text()
    return len(_BOXED.findall(src)), len(_ANY_BLOCK.findall(src))


def audit_enclosure(sections: Path, source_bands: dict[str, dict],
                    section_files: dict[str, str]) -> list[Finding]:
    """A section boxed far more than the band it was built from is drift.

    Type, weight, shadow, radius and gap are audited against the design
    system's RECORDED scale — a closed set the designer chose. Enclosure has no
    such token; what it has is the source: the scout measures, per band, what
    share of visible blocks are bordered or shadowed, and that share travels
    with the winner record. So the reference here is the source band, and the
    tolerance is not a number picked in this file — a section is flagged only
    when its boxed share exceeds the HIGHEST share found across every source
    band on the page. The sources define the envelope. A category that boxes
    40% of its blocks permits 40% here; one that boxes 7% does not permit 33%.

    Measured on voiceowl before this existed: sources at 7%, 15%, 17%; the
    built page at 33%, with nine `border-border bg-card` containers in one
    section. No token was violated, so no audit noticed.
    """
    shares = []
    for w in source_bands.values():
        e = (w or {}).get("enclosure") or {}
        n = int(e.get("blocks") or 0)
        if n:
            shares.append((int(e.get("bordered") or 0) + int(e.get("shadowed") or 0)) / n)
    if not shares:
        return []
    ceiling = max(shares)

    out: list[Finding] = []
    for sid, fname in section_files.items():
        path = sections / fname
        if not path.is_file():
            continue
        boxed, total = enclosure_of(path)
        if total == 0:
            continue
        share = boxed / total
        src = (source_bands.get(sid) or {}).get("enclosure") or {}
        src_n = int(src.get("blocks") or 0)
        src_share = ((int(src.get("bordered") or 0) + int(src.get("shadowed") or 0)) / src_n
                     if src_n else None)
        # Flag against the page-wide ceiling; report against the section's own
        # source so the fixer knows what this band actually looks like.
        # Flag when the section is boxed beyond the page-wide ceiling AND by
        # more than one container over what the ceiling would allow for its
        # size — so a 4-container section at 25% vs a 17% ceiling (one box
        # either way) is not a finding, and a 15-container one at 40% is.
        if share > ceiling and boxed > int(ceiling * total) + 1:
            out.append(Finding(
                fname, 0, "over-enclosed",
                f"{boxed} of {total} containers are boxed ({share:.0%}); "
                + (f"the source band for this section boxes {src_share:.0%}, "
                   if src_share is not None else "")
                + f"and no source on this page boxes more than {ceiling:.0%}. "
                  "Separate by space, rules or ground instead of borders and cards."))
    return out


_H1 = re.compile(r"<h1\b[^>]*?className=(?:\"([^\"]*)\"|\{`([^`]*)`\}|\{\s*cn\(([^)]*)\)\s*\})", re.S)
_HIDDEN = re.compile(r"\b(sr-only|hidden|invisible|opacity-0|text-transparent)\b")


def audit_display(sections: Path, ds: DesignSystem, hero_file: str | None) -> list[Finding]:
    """The hero's h1 carries the display step the design system recorded for it.

    §6: the director's recorded decisions are what the builder is held to.
    The record here says which type step is the display step and what it is
    for; the check is only that the hero's h1 wears it and can be seen. No
    size of this file's — a design system that records a 40px display step
    passes at 40px.

    A hidden h1 is a finding, not a verdict: the sources hide theirs only
    where a canvas draws the text (`heading_drawn`, measured). A builder that
    does the same can dispute; one that hid the name and drew nothing cannot.
    Measured on a real build: `interior_how` copied a source's visually-hidden
    h1 without the canvas that justified it, and the page opened on a 16px
    invisible name and a 36px role.
    """
    if not hero_file or not ds.type_steps:
        return []
    path = sections / hero_file
    if not path.is_file():
        return []
    display = next((st for st in ds.type_steps if st.name.lower() in ("display", "h1", "hero")),
                   ds.type_steps[0])
    want = {m.group(0) for m in TEXT_STEP.finditer(display.classes)}
    src = path.read_text()
    m = _H1.search(src)
    if not m:
        return [Finding(hero_file, 1, "display-step-missing",
                        f"no <h1> in the hero; the design system's `{display.name}` step "
                        f"({display.classes}) is recorded for: {display.use}")]
    line = src[:m.start()].count("\n") + 1
    cls = m.group(1) or m.group(2) or m.group(3) or ""
    have = {bare(c) for c in cls.split()}
    out = []
    if _HIDDEN.search(cls):
        out.append(Finding(hero_file, line, "h1-hidden",
                           "the hero's h1 is visually hidden. The sources hide theirs only "
                           "where a canvas draws the same text; if yours does, dispute "
                           "this — otherwise the name is shown, in the display step"))
    elif not (want & {c for c in have}):
        out.append(Finding(hero_file, line, "display-step-missing",
                           f"the hero's h1 does not carry the design system's `{display.name}` "
                           f"step ({display.classes}), which is recorded for: {display.use}"))
    return out


def audit_dir(sections: Path, ds: DesignSystem,
              source_bands: dict[str, dict] | None = None,
              section_files: dict[str, str] | None = None) -> list[Finding]:
    out: list[Finding] = []
    for p in sorted(sections.glob("*.tsx")):
        out.extend(audit_file(p, ds))
    if source_bands and section_files:
        out.extend(audit_enclosure(sections, source_bands, section_files))
    if section_files:
        out.extend(audit_display(sections, ds, section_files.get("hero")))
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

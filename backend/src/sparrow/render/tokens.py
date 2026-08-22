"""Render `DesignSystem` into the two forms that consume it.

`to_css` produces what the browser reads. `to_prompt` produces what agents read.
Both are derived; neither is authored. Keeping two hand-maintained copies of the
same decision is the failure mode this module exists to remove — it is the same
bug Lovable documents in its own prompt (HSL values drifting between index.css
and tailwind.config.ts), one layer up.
"""

from __future__ import annotations

import re

from sparrow.blackboard.schema import DesignSystem

CSS_BEGIN = "/* ===== SPARROW DESIGN SYSTEM BEGIN — generated, do not edit ===== */"
CSS_END = "/* ===== SPARROW DESIGN SYSTEM END ===== */"

_BLOCK = re.compile(
    re.escape(CSS_BEGIN) + r".*?" + re.escape(CSS_END),
    re.DOTALL,
)


def to_css(ds: DesignSystem) -> str:
    """The `:root` block, fenced so it can be replaced idempotently."""
    lines = [CSS_BEGIN, ":root {"]
    for c in ds.colors:
        lines.append(f"    --{c.token}: {c.value};  /* {c.name} — {c.role} */")
    lines.append(f"    --radius: {ds.radius_base};")
    lines.append("}")
    lines.append(CSS_END)
    return "\n".join(lines)


def apply_to_stylesheet(css: str, ds: DesignSystem) -> str:
    """Replace the fenced block in an existing stylesheet, or append it."""
    block = to_css(ds)
    if _BLOCK.search(css):
        return _BLOCK.sub(block, css)
    return css.rstrip() + "\n\n" + block + "\n"


def to_prompt(ds: DesignSystem) -> str:
    """The fragment injected into every generation call.

    Each scale states its own closure. See `Scale.closure` and
    experiments/drift-test-01 for why that sentence is load-bearing.
    """
    out: list[str] = []

    out.append(f"ATMOSPHERE\n  {ds.atmosphere}")
    out.append("")
    out.append(f"SIGNATURE — the one thing this page is remembered by\n  {ds.signature}")
    out.append("  Everything around it stays quiet. Boldness is spent here and nowhere else.")
    if ds.key_characteristics:
        out.append("")
        out.append("KEY CHARACTERISTICS")
        for k in ds.key_characteristics:
            out.append(f"  - {k}")
    out.append("")
    out.append("PALETTE")
    for c in ds.colors:
        out.append(f"  --{c.token}  \"{c.name}\"  {c.value}  — {c.role}")
    out.append(f"  {ds.color_scale().closure()}")
    for lo, hi in ds.forbidden_hues:
        out.append(f"  FORBIDDEN: no colour at any chroma with hue {lo}–{hi}.")

    out.append("")
    out.append(f"TYPE — {ds.font_family}.")
    weights = ", ".join(str(w) for w in ds.font_weights)
    out.append(
        f"  Weights {weights} only — never {max(ds.font_weights) + 100} or above. "
        f"{ds.weight_scale().closure()}"
    )
    for st in ds.type_steps:
        out.append(f"  {st.name}: {st.classes}  — {st.use}")
    out.append(f"  {ds.type_scale().closure()} Any size not listed above is off-scale.")

    out.append("")
    out.append("SPACING — every value below is exhaustive for its category.")
    out.append(f"  section padding: {ds.section_padding}")
    out.append(f"  container: {ds.container}")
    out.append(f"  grid gap: {ds.grid_gap}")
    out.append(f"  inline flex gap: {ds.inline_gap}  — the only permitted inline gap")
    out.append(f"  stack rhythm: {ds.stack_tight} tight, {ds.stack_loose} loose")

    out.append("")
    out.append("RADIUS")
    out.append(f"  base: {ds.radius_base}")
    out.append(f"  cards and buttons: {ds.radius_card}")
    out.append(f"  inputs: {ds.radius_input}")
    out.append(f"  fully round: {ds.radius_full_allowed} — nothing else")

    out.append("")
    out.append("SHADOWS — two, and only two.")
    out.append(f"  resting: {ds.shadow_rest}")
    out.append(f"  hover: {ds.shadow_hover}")
    out.append("  No coloured shadows, no glows, nothing larger.")

    out.append("")
    out.append(f"IMAGERY TREATMENT\n  {ds.imagery_treatment}")
    out.append("")
    out.append(f"MOTION\n  {ds.motion}")
    return "\n".join(out)


FIDELITY = (
    "Use ONLY the fonts, colors, spacing, and component styles defined in the design "
    "system. Do not introduce any fonts, colors, or visual styles not in the design system."
)

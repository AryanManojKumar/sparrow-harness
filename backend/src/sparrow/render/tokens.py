"""Render `DesignSystem` into the two forms that consume it.

`to_css` produces what the browser reads. `to_prompt` produces what agents read.
Both are derived; neither is authored. Keeping two hand-maintained copies of the
same decision is the failure mode this module exists to remove — it is the same
bug Lovable documents in its own prompt (HSL values drifting between index.css
and tailwind.config.ts), one layer up.
"""

from __future__ import annotations

import re
import json
from pathlib import Path

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
    lines.append("    /* families are bound in layout.tsx via next/font */")
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
    fonts = f"{ds.font_display} for display"
    if ds.font_body != ds.font_display:
        fonts += f", {ds.font_body} for body"
    if ds.font_mono:
        fonts += f", {ds.font_mono} for code/IDs"
    out.append(f"TYPE — {fonts}.")
    out.append("  Use `font-display`, `font-body` and `font-mono` — the families are "
               "already loaded and bound to those utilities. Never name a family directly.")
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
    if getattr(ds, "radius_scale", None):
        out.append(f"  the full radius scale this page may use: {', '.join(ds.radius_scale)}")
    out.append(f"  inputs: {ds.radius_input}")
    out.append(f"  fully round: {ds.radius_full_allowed}")

    out.append("")
    # "SHADOWS — two, and only two. No coloured shadows, no glows, nothing
    # larger." was the line here, and it is why every surface on every page
    # carried the same shadow-sm: a rule of this file's, not a decision of the
    # designer's. What the page may use is now whatever the designer recorded,
    # sized from the sources' measured vocabulary, and the audit holds to that.
    out.append("SHADOWS")
    out.append(f"  resting: {ds.shadow_rest}")
    out.append(f"  hover: {ds.shadow_hover}")
    if getattr(ds, "shadow_scale", None):
        out.append(f"  the full shadow scale this page may use: {', '.join(ds.shadow_scale)}")

    out.append("")
    out.append("WIDTHS — the composition pass says which one this section uses.")
    out.append(f"  contained: {ds.container}")
    out.append(f"  wide: {ds.container_wide or ds.container}")
    out.append(f"  full-bleed: {ds.container_bleed or 'w-full'} — no max-width on the "
               "outer wrapper; inset only what needs reading width")
    out.append("")
    out.append("VERTICAL RHYTHM — not every section breathes the same amount.")
    out.append(f"  standard: {ds.section_padding}")
    out.append(f"  tight: {ds.section_padding_tight or ds.section_padding}")
    out.append(f"  loose: {ds.section_padding_loose or ds.section_padding}")
    if ds.treatments:
        out.append("")
        out.append("TREATMENTS — the open half of this system. Implement the ones whose")
        out.append("`where` covers your section; `how` is written to be used as given.")
        for t in ds.treatments:
            out.append(f"  {t.name} — {t.where}")
            out.append(f"      {t.how}")
    out.append("")
    out.append(f"IMAGERY TREATMENT\n  {ds.imagery_treatment}")
    out.append("")
    out.append(f"MOTION — implement this; it is a requirement, not a mood\n  {ds.motion}")
    if ds.arrival:
        out.append("")
        out.append("ARRIVAL — what happens as the reader reaches a section. Bind these to")
        out.append("whileInView below the first screenful, so they play when they are seen.")
        out.append(f"  {ds.arrival}")
    return "\n".join(out)


FIDELITY = (
    "Use ONLY the fonts, colors, spacing, and component styles defined in the design "
    "system. Do not introduce any fonts, colors, or visual styles not in the design system."
)


# --- font wiring ------------------------------------------------------------

def _var(name: str) -> str:
    """Google family name -> the identifier next/font/google actually exports.

    Spaces become underscores and the family's own casing is preserved:
    "Barlow Condensed" -> Barlow_Condensed, "IBM Plex Mono" -> IBM_Plex_Mono.
    Stripping to PascalCase produces `BarlowCondensed`, which does not exist and
    fails with an opaque "Can't resolve 'next/font/google/target.css'".
    """
    return "_".join(part for part in name.replace("-", " ").split() if part)


def _slug(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def family_weights(workspace: Path | None) -> dict[str, list[str]]:
    """Which weights each family actually publishes, per next/font's own data.

    `next/font/google` types every family's `weight` as a literal union of the
    weights Google serves for it, so asking for one it does not have is a
    compile error, not a fallback. Measured on ashfall: the design system chose
    400-800 and the binder applied that list to all three families — Saira and
    Saira Condensed publish 800, IBM Plex Mono stops at 700, and the build died
    on one line of layout.tsx that no section owns and the repairer cannot see.

    Read from the workspace's own node_modules rather than the network: it is
    the exact table the compiler will check against, it is already on disk, and
    it cannot drift from the installed Next.
    """
    if workspace is None:
        return {}
    root = workspace / "node_modules"
    hits = list(root.glob(".pnpm/next@*/node_modules/next/dist/compiled/@next/font/"
                          "dist/google/font-data.json"))
    hits += list(root.glob("next/dist/compiled/@next/font/dist/google/font-data.json"))
    for f in hits:
        try:
            data = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        return {k: [w for w in (v.get("weights") or []) if w.isdigit()]
                for k, v in data.items() if isinstance(v, dict)}
    return {}


def font_imports(ds: DesignSystem,
                 workspace: Path | None = None) -> tuple[str, str, str]:
    """next/font/google declarations for the families the design agent chose.

    Returns (import line, const declarations, className expression). A design
    system that names a face nothing loads is a design system the builder cannot
    honour — this closes that gap at render time rather than hoping.
    """
    fams: dict[str, str] = {"display": ds.font_display, "body": ds.font_body}
    if ds.font_mono:
        fams["mono"] = ds.font_mono
    uniq = {name: (_var(name), _slug(name)) for name in dict.fromkeys(fams.values())}

    imp = ("import { " + ", ".join(sorted(v for v, _ in uniq.values()))
           + ' } from "next/font/google";')
    # `weight` is REQUIRED for non-variable families and harmless for variable
    # ones. Omitting it fails as an opaque "Can't resolve
    # 'next/font/google/target.css'" — the real message only appears one line
    # further down: "Missing weight for Barlow Condensed."
    # PER FAMILY, not one list for all of them. A family that does not publish
    # the weight it is asked for is a hard compile error in next/font's types.
    published = family_weights(workspace)
    want = [str(w) for w in sorted(ds.font_weights)]

    def weights_for(family: str) -> str:
        have = published.get(family)
        keep = [w for w in want if w in have] if have else list(want)
        # Never emit an empty list — that is the opaque "Missing weight for X".
        return ", ".join(f'"{w}"' for w in (keep or ["400"]))

    consts = "\n".join(
        f'const {slug} = {ident}({{ subsets: ["latin"], display: "swap", '
        f'weight: [{weights_for(name)}], variable: "--font-{slug}" }});'
        for name, (ident, slug) in uniq.items()
    )
    theme = "\n".join(
        f"    --font-{role}: var(--font-{uniq[name][1]});" for role, name in fams.items()
    )
    # The recorded weights as utilities too. The director writes its type steps
    # as `font-500`, the builder copies them, and Tailwind v4 has no such class
    # unless the theme declares `--font-weight-500` — measured on voiceowl: 112
    # numeric weight utilities across ten sections, every one silently dropped,
    # every heading rendered at 400 against a recorded 500. `font-medium` and
    # `font-500` now both resolve.
    theme += "\n" + "\n".join(
        f"    --font-weight-{w}: {w};" for w in sorted(set(ds.font_weights)))
    cls = " ".join(f"${{{slug}.variable}}" for _, slug in uniq.values())
    return imp, consts, f"{cls}|||{theme}"


# --- font validation --------------------------------------------------------

_CATALOG: set[str] | None = None
_CATALOG_PATH = Path.home() / ".cache" / "sparrow" / "google-fonts.txt"


def google_families(refresh: bool = False) -> set[str]:
    """Every family Google Fonts actually serves, cached on disk.

    `design_director` picks fonts by name and cannot be handed a 1,500-entry
    list in its prompt, so the names it invents have to be checked. An unknown
    family fails as `Can't resolve 'next/font/google/target.css'` with
    "Unknown font" — in layout.tsx, which no section owns, so the repairer
    cannot reach it. Catch it at the point of choice instead.
    """
    global _CATALOG
    if _CATALOG is not None and not refresh:
        return _CATALOG
    if _CATALOG_PATH.exists() and not refresh:
        _CATALOG = set(_CATALOG_PATH.read_text().splitlines())
        return _CATALOG

    import json
    import urllib.request

    req = urllib.request.Request(
        "https://fonts.google.com/metadata/fonts",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8")
    raw = raw[raw.index("{"):]                       # strip the XSSI prefix
    fams = {f["family"] for f in json.loads(raw)["familyMetadataList"]}
    _CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CATALOG_PATH.write_text("\n".join(sorted(fams)))
    _CATALOG = fams
    return fams


def validate_fonts(ds: DesignSystem) -> dict[str, list[str]]:
    """Return {bad_family: [near misses]}. Empty dict means all resolve."""
    import difflib

    fams = google_families()
    bad: dict[str, list[str]] = {}
    for name in {ds.font_display, ds.font_body, ds.font_mono}:
        if name and name not in fams:
            bad[name] = difflib.get_close_matches(name, fams, n=4, cutoff=0.5)
    return bad

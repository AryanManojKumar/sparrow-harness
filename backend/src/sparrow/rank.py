"""Source ranking — turning extracted sites into evidence the design agent reads.

Three steps, in increasing cost:

1. COMMONALITY. Pure counting, no model. What section types does this category's
   pages actually contain, and in what order? Convention is information — but
   convention is not a requirement, so this informs the sitemap, never dictates it.

2. PRIMARY REFERENCE. One cheap call. Which single site's SKELETON best fits this
   brief? CLAUDE.md §5: blending six sites yields the mean of six sites. One site
   owns the rhythm; the rest are a checklist.

3. PER-SECTION STRUCTURE. One cheap call per section type, all candidates in it.
   Which site's version of this section is best STRUCTURED for this brief — not
   which looks nicest.

What is ranked is structure. Visual direction stays with `design_director` and
comes from one place, or the result is six good sections that do not belong on the
same page.

The rubric is concrete on purpose. "Which is best" produces the same failure as a
taste-judging observer: it approves anything on turn one and nitpicks on turn three.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from sparrow.blackboard.schema import Brief
from sparrow.providers import Provider, Tier

_JSON = re.compile(r"\{.*\}", re.DOTALL)

# Page chrome. Every site has a nav and a footer, so COUNTING them says nothing —
# letting them into the prevalence order once put `nav` second. But excluding them
# from the count is not the same as excluding them from the PAGE, and conflating
# the two shipped a site with no navigation and no footer, which reads as half
# built because it is.
#
# So: never ranked, always built. `CHROME` is required and prepended/appended to
# every sitemap; `other` is the classifier's "I could not tell" bucket and is
# neither ranked nor built.
CHROME = ("nav", "footer")
NOT_SECTIONS = {*CHROME, "other"}

# Types worth ranking.
RANKABLE = {
    "hero", "logo-wall", "feature-grid", "feature-detail", "product-showcase",
    "testimonial", "pricing", "faq", "comparison", "integration-grid", "stats", "cta",
}


@dataclass
class Candidate:
    """One site's version of one section type."""

    site: str
    section_type: str
    position: int          # 1-based order on its own page
    height: int
    words: int
    images: int
    buttons: int
    list_items: int
    headings: list[str]
    text: str
    unrendered: bool = False

    def line(self) -> str:
        return (
            f"[{self.site}] pos {self.position} · {self.height}px · {self.words}w · "
            f"{self.images} img · {self.buttons} btn · {self.list_items} li"
            f"{' · TEXT NOT RENDERED' if self.unrendered else ''}\n"
            f"    heading: {'; '.join(self.headings[:2]) or '—'}\n"
            f"    copy: {self.text[:150]}"
        )


@dataclass
class Commonality:
    """What this category's pages contain, counted rather than guessed."""

    sites: int
    counts: Counter = field(default_factory=Counter)
    typical_order: list[str] = field(default_factory=list)

    def conventional(self, threshold: float = 0.6) -> list[str]:
        """Section types present on at least `threshold` of the sources."""
        need = max(2, round(self.sites * threshold))
        return [t for t, n in self.counts.most_common()
                if n >= need and t not in NOT_SECTIONS]

    def report(self) -> str:
        lines = [f"{self.sites} sources examined.", "", "Section types by prevalence:"]
        for t, n in self.counts.most_common():
            if t in NOT_SECTIONS:
                continue
            bar = "#" * n
            lines.append(f"  {t:<20} {n}/{self.sites} {bar}")
        skipped = {t: n for t, n in self.counts.items() if t in NOT_SECTIONS}
        if skipped:
            lines.append("  (chrome and unclassified, excluded: "
                         + ", ".join(f"{t} {n}/{self.sites}" for t, n in skipped.items()) + ")")
        lines.append("")
        lines.append(f"Conventional for this category: {', '.join(self.conventional())}")
        lines.append(f"Typical order: {' -> '.join(self.typical_order)}")
        return "\n".join(lines)


def commonality(labelled: dict[str, list[tuple[str, int]]]) -> Commonality:
    """Count section types across sources. Deterministic; costs nothing.

    `labelled` maps site -> [(section_type, position), ...].
    """
    c = Commonality(sites=len(labelled))
    for types in labelled.values():
        for t, _ in {(t, 0) for t, _ in types}:  # count each type once per site
            c.counts[t] += 1

    # Typical order: mean position of each conventional type across sources.
    positions: dict[str, list[float]] = {}
    for types in labelled.values():
        n = max((p for _, p in types), default=1)
        for t, p in types:
            positions.setdefault(t, []).append(p / n)
    conv = set(c.conventional())          # already excludes chrome and `other`
    c.typical_order = [
        t for t, _ in sorted(
            ((t, sum(v) / len(v)) for t, v in positions.items() if t in conv),
            key=lambda kv: kv[1],
        )
    ]
    return c


PRIMARY_SYSTEM = """You pick ONE reference site whose page SKELETON best fits a brief.

You are not judging looks — you cannot see these sites. You are judging structure: what
sections exist, in what order, at what density, and whether that shape serves this
audience and this offering.

Score each site on four axes, then pick one:
- FIT: does its section sequence match what this brief needs to communicate?
- DEPTH: does it carry enough sections to fill a real page, without padding?
- PACING: does it alternate weight sensibly, or is it a wall of equal blocks?
- AUDIENCE: does its density and copy volume suit this brief's reader?

Blending is not an option. One site owns the rhythm; naming a second as "also good"
defeats the purpose.

JSON only:
{"primary": "<site>", "why": "<one sentence tied to the brief>",
 "runner_up": "<site>", "rejected": {"<site>": "<one clause>"}}"""


def pick_primary(
    provider: Provider, brief: Brief, labelled: dict[str, list[tuple[str, int]]]
) -> tuple[str, str, object]:
    lines = []
    for site, types in labelled.items():
        seq = " -> ".join(t for t, _ in sorted(types, key=lambda x: x[1]))
        lines.append(f"{site}: {seq}")
    user = (
        f"<brief>\nOffering: {brief.offering}\nAudience: {brief.audience}\n"
        f"Tone: {brief.tone}\nPrimary action: {brief.primary_action}\n</brief>\n\n"
        "<skeletons>\n" + "\n".join(lines) + "\n</skeletons>"
    )
    res = provider.complete(tier=Tier.CHEAP, system=PRIMARY_SYSTEM, user=user, max_tokens=2000)
    m = _JSON.search(res.text)
    if not m:
        raise ValueError(f"no JSON from primary selection: {res.text[:200]}")
    d = json.loads(m.group(0))
    return d["primary"], d.get("why", ""), res


SECTION_SYSTEM = """You rank several sites' versions of ONE section type, for one brief.

You cannot see them. Judge STRUCTURE from the measurements and copy given:

- COVERAGE: does it carry the elements this section needs to do its job for this brief?
- DENSITY: is the copy volume right for this audience — technical readers tolerate more,
  consumers less?
- EVIDENCE: does it show something concrete (a product, a number, a name) or only assert?
- ECONOMY: does every element earn its place, or is it padded to fill space?

A section whose text did not render is missing its copy, not lacking it — rank it on its
counts alone and say so.

Rank all candidates. The winner's structure will be adapted, never copied: a different
brand, different copy, a different design system.

JSON only:
{"winner": "<site>", "why": "<one sentence tied to this brief>",
 "order": ["<site>", ...],
 "adopt": ["<2-4 concrete structural elements worth carrying over>"]}"""


def rank_section(
    provider: Provider, brief: Brief, section_type: str, candidates: list[Candidate]
) -> tuple[dict, object]:
    if len(candidates) < 2:
        only = candidates[0].site if candidates else None
        return (
            {"winner": only, "why": "only candidate — not a ranked choice",
             "order": [only] if only else [], "adopt": [], "unopposed": True},
            None,
        )
    user = (
        f"<brief>\nOffering: {brief.offering}\nAudience: {brief.audience}\n"
        f"Tone: {brief.tone}\n</brief>\n\n"
        f"<section_type>{section_type}</section_type>\n\n"
        "<candidates>\n" + "\n\n".join(c.line() for c in candidates) + "\n</candidates>"
    )
    res = provider.complete(tier=Tier.CHEAP, system=SECTION_SYSTEM, user=user, max_tokens=2500)
    m = _JSON.search(res.text)
    if not m:
        raise ValueError(f"no JSON ranking {section_type}: {res.text[:200]}")
    return json.loads(m.group(0)), res


def register_report(registers: dict[str, object]) -> str:
    """Counted visual conventions. Facts to weigh, not a palette to copy."""
    n = len(registers) or 1
    dark = sum(1 for r in registers.values() if r.dark)
    video = sum(1 for r in registers.values() if r.video)
    canvas = sum(1 for r in registers.values() if r.canvas)
    code = sum(1 for r in registers.values() if r.code_blocks > 5)
    imgs = sum(r.product_images for r in registers.values()) / n

    lines = ["VISUAL CONVENTIONS IN THIS CATEGORY (counted, not copied)"]
    lines.append(f"  dark-grounded pages:   {dark}/{n}"
                 + ("  — dark is the category norm here" if dark > n / 2
                    else "  — the category is split" if dark else
                    "  — the category is light-grounded"))
    lines.append(f"  pages using video:     {video}/{n}")
    lines.append(f"  pages using canvas:    {canvas}/{n}")
    lines.append(f"  pages showing code:    {code}/{n}")
    lines.append(f"  large product images:  {imgs:.0f} per page on average")

    mots = [r.motion for r in registers.values() if getattr(r, "motion", None)]
    if mots:
        ambient = sum(1 for m in mots if m.running > 3)
        moving = sum(1 for m in mots if m.transform)
        tempos = sorted(m.tempo_ms for m in mots if m.tempo_ms)
        names = sorted({a for m in mots for a in m.ambient})[:6]
        lines.append("")
        lines.append("  MOTION")
        lines.append(f"    always-running motion: {ambient}/{n}"
                     + (f"  — e.g. {', '.join(names)}" if names else ""))
        lines.append(f"    animate transform/position (not just colour): {moving}/{n}")
        if tempos:
            mid = tempos[len(tempos) // 2]
            lines.append(f"    interaction tempo: {mid}ms typical "
                         f"(range {tempos[0]}-{tempos[-1]}ms)")
        eas = sorted({m.easing for m in mots if m.easing})[:3]
        if eas:
            lines.append(f"    easing in use: {'; '.join(eas)}")
        lines.append("    Not measurable from a page: scroll choreography driven by "
                     "IntersectionObserver or a JS timeline. Tempo and register are "
                     "evidence; sequence is your decision.")
    lines.append("")
    lines.append("  These are conventions, not requirements. Following one is a choice you")
    lines.append("  should be able to justify; departing from one is also a choice. What you")
    lines.append("  must not do is land on a register by default without noticing there was")
    lines.append("  a decision to make.")
    return "\n".join(lines)


def to_design_brief(
    comm: Commonality, primary: str, primary_why: str, rankings: dict[str, dict],
    registers: dict[str, object] | None = None,
) -> str:
    """The <sources> block `design_director` reads.

    Structure only. It deliberately carries no colours, fonts or spacing — the
    visual direction is the design agent's to decide, and handing it six sites'
    aesthetics is how a page ends up looking like six sites.
    """
    out = [comm.report(), ""]
    if registers:
        out += [register_report(registers), ""]
    out += [f"PRIMARY REFERENCE: {primary}", f"  {primary_why}",
           "  Its section order and pacing are the skeleton. Its look is NOT.", ""]
    out.append("BEST-STRUCTURED VERSION OF EACH SECTION")
    for t in comm.typical_order:
        r = rankings.get(t)
        if not r:
            continue
        tag = " (unopposed)" if r.get("unopposed") else ""
        out.append(f"  {t}: {r['winner']}{tag} — {r['why']}")
        for a in r.get("adopt", []):
            out.append(f"      adopt: {a}")
    out.append("")
    out.append("These are structural patterns to adapt, never designs to reproduce. "
               "Extracting layout patterns is fine; reproducing a company's "
               "distinctive look for their competitor is not.")
    return "\n".join(out)

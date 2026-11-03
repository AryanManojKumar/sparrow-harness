"""Guardrails for a site the agent designed: what Sparrow still holds it to.

Experiment dsh-builder-02 settled who designs: the agent, from the references.
What it does not settle is truth and ownership, and those are Sparrow's:

- **claims** — names and figures on the page that the owner never gave;
- **assets** — the curated material the run paid for reaches the page, and
  nothing points at a file that does not exist;
- **brand** — the page does not wear a reference's signature colour (§5);
- **links** — every link lands somewhere;
- **crop** — an image shows enough of itself to be read;
- **covered** — no image is painted over the page's text;
- **motion** — the motion the chosen direction specifies is built;
- **arrival** — the page stages entrances at the sources' measured rate;
- **type** — the headline scale is the main reference's, not the stack's default.

Each check is deterministic and each finding is phrased as something the agent
can act on, because the findings ARE the next prompt — the same "an audit that
fails and a fixer that acts" shape CLAUDE.md §6 found is the only thing that
moves a builder.

The claim check is looser than `audit.audit_claims` on purpose. That one reads
section files Sparrow's own builder wrote from drafted copy; a free designer
writes display type — "ENTER THE FIELD", step numbers "01"–"04" — and on B+ the
strict check flagged 25 tokens of which none was a fact. A fixer handed 25
false alarms strips good headlines, so a line set entirely in capitals is read
for numbers only, ordinals are furniture, and a capital after a full stop is a
sentence starting.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from sparrow.audit import _TOKEN, visible_text

_ASSET_REF = re.compile(r"""/assets/([A-Za-z0-9_./-]+\.(?:png|jpe?g|webp|svg|gif|avif|mp4|webm))""")
_ORDINAL = re.compile(r"^0\d$")


@dataclass
class Finding:
    kind: str        # claim | missing-asset | unused-asset | brand | link | crop | covered | motion | arrival | type
    where: str       # a file, a page, or "page"
    detail: str

    def line(self) -> str:
        return f"- [{self.kind}] {self.where}: {self.detail}"


def source_files(workspace: Path) -> list[Path]:
    src = workspace / "src"
    return sorted(p for p in src.rglob("*.tsx") if "/components/ui/" not in p.as_posix()) \
        if src.is_dir() else []


def claims_in(code: str, confirmed: set[str]) -> list[str]:
    out: set[str] = set()
    for text in visible_text(code):
        text = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", text)
        letters = [c for c in text if c.isalpha()]
        shouting = bool(letters) and all(c.isupper() for c in letters)
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            toks = [t.strip(".,+’'") for t in _TOKEN.findall(sentence)]
            for i, t in enumerate(toks):
                if len(t) < 2 or _ORDINAL.match(t) or t.lower() in confirmed:
                    continue
                numeric = any(c.isdigit() for c in t)
                capital = (not shouting and t[:1].isupper()
                           and not (i == 0 and len(toks) > 1))
                if numeric or capital:
                    out.add(t)
    return sorted(out)


def check_claims(workspace: Path, confirmed: set[str]) -> list[Finding]:
    out = []
    for p in source_files(workspace):
        bad = claims_in(p.read_text(errors="ignore"), confirmed)
        if bad:
            out.append(Finding("claim", p.relative_to(workspace).as_posix(),
                               f"names or figures the owner never gave: {', '.join(bad[:15])}. "
                               "If any is a name, number, place, platform, customer or "
                               "credential, remove it or use a visible placeholder like "
                               "`[Your price]`; ordinary words styled as display type are fine"))
    return out


def check_assets(workspace: Path, curated: list[str]) -> list[Finding]:
    """`curated` is the filenames the asset stage produced, under public/assets/."""
    code = "\n".join(p.read_text(errors="ignore") for p in source_files(workspace))
    public = workspace / "public" / "assets"
    out: list[Finding] = []
    for name in sorted(set(_ASSET_REF.findall(code))):
        if not (public / name).is_file():
            out.append(Finding("missing-asset", "page",
                               f"points at /assets/{name}, which does not exist. Use a file "
                               "that exists, or generate one with generate_asset"))
    # Any crop of an asset counts as using it: `hero-1--card.webp` shows hero-1.
    unused = [n for n in curated if n.rsplit(".", 1)[0].split("--")[0] not in code]
    if unused:
        out.append(Finding("unused-asset", "page",
                           f"curated for this product and not shown anywhere: "
                           f"{', '.join(unused)}. Place each where the page calls for imagery"))
    return out


def check_brand(hits: list[dict]) -> list[Finding]:
    seen, out = set(), []
    for h in hits:
        if h["page"] in seen:
            continue
        seen.add(h["page"])
        out.append(Finding("brand", "page",
                           f"the page's {h['page']} (on {h['share']:.1%} of it) is ΔE "
                           f"{h['delta_e']} from {h['site']}'s {h['reference']} — the same "
                           "colour to a visitor. That is a reference's brand; move this "
                           "accent to a clearly different hue of the site's own"))
    return out


def check_links(broken: list[dict]) -> list[Finding]:
    return [Finding("link", b.get("page", "/"),
                    f'"{b.get("text", "")}" → {b.get("href")}: {b.get("problem")}')
            for b in broken[:30]]


# How much of an image must show. Measured on twenty-crm: the agent framed the
# owner's 1600x1000 images in 590x179 strips of an 800x800 centre crop, 19% of
# each file — the reader saw each image's title and none of the product.
# Emergent, same files, showed 67-71%.
MIN_SHOWN = 0.6


def _original(name: str) -> str:
    """`hero-1--card.png` → `hero-1.png`: a derived crop names its original."""
    stem, _, ext = name.rpartition(".")
    return f"{stem.split('--')[0]}.{ext}"


def check_crops(images: list[dict], originals: dict[str, tuple[int, int]]) -> list[Finding]:
    """Curated images that show less than `MIN_SHOWN` of the original file.

    `images` is the workshop's measurement of the page; `originals` maps each
    curated file name to its size. A `--card` crop already lost part of the
    file before the page cropped it again, and both count.
    """
    worst: dict[str, tuple[float, dict]] = {}
    for im in images:
        name = im["src"].split("?")[0].rsplit("/", 1)[-1]
        orig = _original(name)
        if orig not in originals:
            continue
        (ow, oh), (nw, nh) = originals[orig], im.get("natural") or (0, 0)
        if not (ow and oh and nw and nh):
            continue
        ro, rv = ow / oh, nw / nh
        shown = im["visible"] * min(ro, rv) / max(ro, rv)
        if shown < worst.get(orig, (1.0, {}))[0]:
            worst[orig] = (shown, im)
    out = []
    for orig, (shown, im) in sorted(worst.items()):
        if shown < MIN_SHOWN:
            w, h = originals[orig]
            out.append(Finding("crop", orig,
                               f"shows {round(shown * 100)}% of the image in a "
                               f"{im['box'][0]}x{im['box'][1]} box — the reader cannot see "
                               f"what it is. Use `{orig}` itself (not a `--` crop) in a box "
                               f"close to its own {w}:{h} shape, or let it show whole."))
    return out


def check_covered(covered: list[dict]) -> list[Finding]:
    """Text with an image painted over it, one finding per image.

    The crop check alone was satisfied the wrong way on twenty-crm's second
    build: the fixer let each image show whole and left it absolutely
    positioned in its card, so every card's title and copy sat underneath.
    """
    by: dict[str, list[str]] = {}
    for c in covered:
        by.setdefault(c["by"], []).append(f"{c['tag']} “{c['text']}”")
    return [Finding("covered", img,
                    f"is painted over the text {', '.join(texts[:4])}"
                    + (f" and {len(texts) - 4} more" if len(texts) > 4 else "")
                    + " — the reader cannot read it. Put the image in the layout flow "
                      "(below or beside the text), not over it.")
            for img, texts in sorted(by.items())]


_MOTION = re.compile(r"whileInView|<motion\.|\banimate=|@keyframes|\banimation\s*:|"
                     r"transition(?:-property|-duration)?\s*:|requestAnimationFrame|"
                     r"\btransition-(?:all|colors|opacity|transform)\b|\banimate-\w+")


def motion_in(workspace: Path) -> int:
    """How many places the site's source moves something."""
    files = source_files(workspace) + sorted((workspace / "src").rglob("*.css")) \
        if (workspace / "src").is_dir() else []
    # Not the imports: every scaffold imports an animation library.
    return sum(len(_MOTION.findall(re.sub(r"(?m)^\s*(@import|import)\b.*$", "",
                                          f.read_text(errors="replace"))))
               for f in files)


def check_motion(workspace: Path, spec: str) -> list[Finding]:
    """A page with no movement at all, against a direction that specifies some."""
    if motion_in(workspace):
        return []
    return [Finding("motion", "page",
                    "nothing on the page moves, and the direction the owner chose specifies: "
                    f"{spec[:500]} Build it: entrances bound to `whileInView` from "
                    "`motion/react` (never on mount), the transitions it names, and any "
                    "always-running element it describes; respect `useReducedMotion`.")]


# A page staging under this share of the sources' entrances moves less than
# they do. Measured on twenty-crm-2: sources 46%, the build 0% — three CSS
# loops passed `check_motion`, which only asked whether anything moved.
ARRIVAL_SHARE = 0.5


def check_arrival(built: dict, sources: dict | None) -> list[Finding]:
    """Entrances on the built page against the sources', by the same probe."""
    if not sources or sources.get("share", 0) < 0.1:
        return []
    # `reach` counts an element staged through a parent: an agent animates a
    # block as one wrapper where a source animates each element (see look._REACH).
    got, want = built.get("reach", built.get("share", 0.0)), sources["share"]
    if got >= want * ARRIVAL_SHARE:
        return []
    how = (f"from opacity {sources.get('from', 0):.0f}"
           + (f", rising {sources['travel']}px" if sources.get("travel") else "")
           + (f", over {sources['ms']}ms" if sources.get("ms") else ""))
    return [Finding("arrival", "page",
                    f"{round(got * 100)}% of the page's elements animate in as the reader "
                    f"reaches them; the reference sites stage {round(want * 100)}% ({how}). "
                    "Stage the section contents — headings, copy, cards, images — to enter "
                    "on arrival with `motion/react` `whileInView` (initial hidden, "
                    "viewport once), keeping `useReducedMotion`.")]


# Below this share of the main reference's largest heading, the page's scale
# is the stack's default rather than the reference's.
TYPE_SHARE = 0.85


def check_type(headings: list[dict], reference: tuple[str, float] | None) -> list[Finding]:
    """The page's largest heading against the main reference's largest."""
    if not reference or not headings:
        return []
    site, ref = reference
    top = max(h["size"] for h in headings)
    if top >= ref * TYPE_SHARE:
        return []
    return [Finding("type", "page",
                    f"the largest heading is {round(top)}px; {site}, the main reference, "
                    f"sets its largest at {round(ref)}px. Bring the headline scale up to "
                    f"at least {round(ref * TYPE_SHARE)}px for the biggest heading and "
                    f"scale the others with it, keeping the hierarchy.")]


def fix_prompt(findings: list[Finding]) -> str:
    return ("Fix what the site's checks found. Change only what each line names; keep "
            "the design as it is.\n\n" + "\n".join(f.line() for f in findings))


def as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]

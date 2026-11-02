"""Guardrails for a site the agent designed: what Sparrow still holds it to.

Experiment dsh-builder-02 settled who designs: the agent, from the references.
What it does not settle is truth and ownership, and those are Sparrow's:

- **claims** — names and figures on the page that the owner never gave;
- **assets** — the curated material the run paid for reaches the page, and
  nothing points at a file that does not exist;
- **brand** — the page does not wear a reference's signature colour (§5);
- **links** — every link lands somewhere.

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
    kind: str        # claim | missing-asset | unused-asset | brand | link
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


def fix_prompt(findings: list[Finding]) -> str:
    return ("Fix what the site's checks found. Change only what each line names; keep "
            "the design as it is.\n\n" + "\n".join(f.line() for f in findings))


def as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]

"""Render design choices as pictures instead of prose.

Gate 2 is the most consequential decision in a run — it fixes every visual choice
downstream — and it was being asked like this:

    "A perforated remittance-advice ribbon carrying real currency pairs…"
    "A hero-scale field-to-funds loom weaves labeled source-system…"

Nobody outside the design agent can choose between those. CLAUDE.md §8 is explicit
that escalation must offer concrete options a business owner can answer, and three
sentences of design vocabulary is the opposite.

So each direction is rendered: its actual palette as swatches, its actual
typefaces at their actual sizes, its signature named in plain words. And alongside
them, what the reference sites are actually painted with — because "do you want
what your competitors have, or not" is a question anyone can answer, and it is the
real question behind light-versus-dark.

Deterministic. HTML through the Playwright already running, no model, no cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sparrow.blackboard.schema import DesignSystem

_FONT_CSS = "https://fonts.googleapis.com/css2?{q}&display=swap"


def _families(ds: DesignSystem) -> str:
    fams = {ds.font_display, ds.font_body} | ({ds.font_mono} if ds.font_mono else set())
    q = "&".join(f"family={f.replace(' ', '+')}:wght@400;500;600" for f in sorted(fams))
    return _FONT_CSS.format(q=q)


def direction_html(ds: DesignSystem, index: int) -> str:
    """One direction, shown rather than described."""
    by = {c.token: c for c in ds.colors}
    swatches = "".join(
        f'<div class="sw"><i style="background:{c.value}"></i>'
        f'<b>{c.name}</b><s>{c.token}</s></div>'
        for c in ds.colors
    )
    bg = by["background"].value
    fg = by["foreground"].value
    pri = by["primary"].value
    prifg = by["primary-foreground"].value
    muted = by["muted"].value
    mutedfg = by["muted-foreground"].value
    border = by["border"].value
    return f"""<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="{_families(ds)}">
<style>
  *{{box-sizing:border-box;margin:0}}
  body{{width:900px;font-family:'{ds.font_body}',system-ui;background:{bg};color:{fg}}}
  .pad{{padding:40px 44px}}
  .eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
    color:{mutedfg};font-weight:600}}
  h1{{font-family:'{ds.font_display}',system-ui;font-size:46px;line-height:1.03;
    letter-spacing:-.02em;font-weight:600;margin:14px 0 12px}}
  p{{font-size:15px;line-height:1.6;color:{mutedfg};max-width:60ch}}
  .row{{display:flex;gap:10px;margin-top:22px;align-items:center}}
  .btn{{background:{pri};color:{prifg};padding:11px 20px;border-radius:8px;
    font-size:14px;font-weight:600}}
  .btn2{{border:1px solid {border};padding:11px 20px;border-radius:8px;font-size:14px}}
  .sws{{display:flex;flex-wrap:wrap;gap:0;background:{muted};border-top:1px solid {border}}}
  .sw{{width:100px;padding:12px 10px}}
  .sw i{{display:block;height:44px;border-radius:6px;border:1px solid {border}}}
  .sw b{{display:block;font-size:10px;margin-top:7px;font-weight:600;line-height:1.25}}
  .sw s{{display:block;font-size:9px;color:{mutedfg};text-decoration:none;
    font-family:'{ds.font_mono or ds.font_body}',monospace}}
  .type{{display:flex;gap:26px;padding:18px 44px;border-top:1px solid {border};
    background:{muted};font-size:11px;color:{mutedfg}}}
  .type b{{color:{fg};font-weight:600}}
  .tag{{position:absolute;top:16px;right:20px;font-size:11px;font-weight:600;
    color:{mutedfg};font-family:'{ds.font_mono or ds.font_body}',monospace}}
</style>
<div class="pad" style="position:relative">
  <div class="tag">OPTION {index + 1}</div>
  <div class="eyebrow">{ds.font_display} &middot; {ds.font_body}</div>
  <h1>{_headline(ds)}</h1>
  <p>{ds.signature}</p>
  <div class="row"><span class="btn">Primary action</span>
    <span class="btn2">Secondary</span></div>
</div>
<div class="sws">{swatches}</div>
<div class="type">
  <span><b>Display</b> {ds.font_display}</span>
  <span><b>Body</b> {ds.font_body}</span>
  {'<span><b>Mono</b> ' + ds.font_mono + '</span>' if ds.font_mono else ''}
  <span><b>Motion</b> {ds.motion.split('.')[0][:58]}</span>
</div>"""


def _headline(ds: DesignSystem) -> str:
    """A short phrase from the atmosphere, so the specimen shows type at real size."""
    first = ds.atmosphere.split(".")[0].strip()
    return (first[:58] + "…") if len(first) > 58 else first


def sources_html(palettes: dict[str, object]) -> str:
    """What the reference sites are actually painted with.

    The real question behind "light or dark" is "do you want what your competitors
    have, or deliberately not" — and that is answerable by anyone once they can see it.
    """
    rows = []
    for site, p in palettes.items():
        chips = "".join(f'<i style="background:{h}"></i>' for h in p.swatches()[:6])
        tone = "dark" if p.dark else "light"
        acc = f'<em>accent {p.accent}</em>' if p.accent else "<em>no strong accent</em>"
        rows.append(f'<div class="r"><span class="s">{site}</span>'
                    f'<span class="chips">{chips}</span>'
                    f'<span class="m">{tone} &middot; {acc}</span></div>')
    dark_n = sum(1 for p in palettes.values() if p.dark)
    return f"""<!doctype html><meta charset="utf-8">
<style>
  *{{box-sizing:border-box;margin:0}}
  body{{width:900px;font-family:ui-sans-serif,system-ui;background:#fff;color:#111;
    padding:32px 36px}}
  h2{{font-size:17px;font-weight:650;margin-bottom:4px}}
  .sub{{font-size:13px;color:#666;margin-bottom:20px}}
  .r{{display:flex;align-items:center;gap:16px;padding:11px 0;
    border-top:1px solid #eaeaea}}
  .s{{width:200px;font-size:13px;font-weight:600}}
  .chips{{display:flex;gap:5px}}
  .chips i{{width:34px;height:34px;border-radius:6px;border:1px solid #0000001a;
    display:block}}
  .m{{font-size:12px;color:#666;margin-left:auto}}
  .m em{{font-style:normal;font-family:ui-monospace,monospace}}
</style>
<h2>What your reference sites are actually painted with</h2>
<div class="sub">{dark_n} of {len(palettes)} use a dark ground.
  Measured from the live pages, not guessed.</div>
{''.join(rows)}"""


@dataclass
class Rendered:
    name: str
    path: Path


def render(html_by_name: dict[str, str], out_dir: Path, width: int = 900) -> list[Rendered]:
    """HTML to PNG. One browser, one page per specimen."""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    made: list[Rendered] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 700},
                                device_scale_factor=2)
        for name, html in html_by_name.items():
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(400)          # let the webfonts paint
            path = out_dir / f"{name}.png"
            page.screenshot(path=str(path), full_page=True)
            made.append(Rendered(name, path))
        browser.close()
    return made


def is_svg(data: bytes) -> bool:
    """Sniffed from the bytes, not from the filename.

    A browser upload arrives with whatever name the user's filesystem had, and
    `logo.png` that is actually an SVG is a normal thing to receive. The two
    formats take completely different paths from here — one is recoloured
    losslessly through `currentColor`, the other is masked — so guessing from
    the suffix picks the wrong path silently.
    """
    head = data[:1024].lstrip()
    return head[:4] == b"<svg" or (head[:5] == b"<?xml" and b"<svg" in data[:4096])


def rasterize_svg(svg: bytes, out: Path, width: int = 512) -> Path:
    """An SVG as pixels, through the Playwright already in the stack.

    Needed in exactly one place: an uploaded logo is passed to the image model
    as a reference so a generated product surface carries the user's real mark,
    and the image API takes PNG/JPEG/WebP — it has no idea what an SVG is. The
    site itself never uses this; there the SVG is used as an SVG, which is the
    whole reason SVG is the preferred logo format.

    Rendered on a TRANSPARENT ground. On white, a mark drawn in near-white ink
    rasterizes to an empty square and the reference tells the image model
    nothing, which is indistinguishable from passing no reference at all.
    """
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    body = svg.decode("utf-8", "replace")
    html = ("<html><body style=\"margin:0;background:transparent\">"
            f"<div style=\"display:inline-block;width:{width}px\">{body}</div>"
            "</body></html>")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": width},
                                device_scale_factor=2)
        page.set_content(html, wait_until="load")
        page.wait_for_timeout(150)
        page.screenshot(path=str(out), omit_background=True,
                        clip=page.locator("div").first.bounding_box())
        browser.close()
    return out

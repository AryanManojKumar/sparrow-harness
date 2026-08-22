"""Scout — extraction from live reference sites.

The hard part is not ranking sections, it is FINDING them. Real sites are React
with hashed class names, lazy content and animation-gated reveals, and very few
use semantic <section> elements. Everything downstream — the per-section ranking,
the commonality pass, the interview-by-screenshot — depends on segmentation
being right, so it is the first thing that has to be proven.

Strategy: segment visually rather than semantically. A landing page section is a
full-bleed horizontal band. Find elements that span the viewport width and have
real height, then keep only the outermost of any nested run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import sync_playwright

_SCROLL = """
async () => {
  const step = window.innerHeight / 2;
  for (let y = 0; y < document.body.scrollHeight; y += step) {
    window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 250));
  }
  window.scrollTo(0, 0);
  await new Promise(r => setTimeout(r, 500));
}
"""

# Candidate bands: full-bleed, tall enough to be a section, not nested inside
# another candidate. Semantic <section>/<header>/<footer> get a nod but are not
# required, because most real sites do not use them.
# Two strategies, tried in order.
#
# 1. SEMANTIC. If the author used <section> (most well-built sites do — Linear
#    has 9, Resend 12, Vercel 10), that is their own segmentation and it beats
#    any heuristic.
# 2. SPINE. Otherwise descend the DOM while there is exactly one full-bleed
#    child that swallows the page, until reaching a node with several tall
#    children. Those siblings are the sections. Descending only ONE level is not
#    enough — real pages nest wrappers 3-6 deep, which is why the first attempt
#    returned the whole page as one band.
_SEGMENT = r"""
(opts) => {
  const vw = document.documentElement.clientWidth;
  const box = (el) => el.getBoundingClientRect();
  const visible = (el) => {
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  };
  const isBand = (el) => {
    if (!visible(el)) return false;
    const r = box(el);
    return r.height >= opts.minHeight && r.width >= vw * 0.9;
  };

  let bands = [];
  let strategy = 'semantic';

  const semantic = [...document.querySelectorAll('section')].filter(el => {
    if (!visible(el)) return false;
    const r = box(el);
    return r.height >= opts.minHeight * 0.5;
  });
  const outerSemantic = semantic.filter(el => !semantic.some(o => o !== el && o.contains(el)));

  if (outerSemantic.length >= 3) {
    bands = outerSemantic;
    // Pull in a header/footer the author left outside <section>.
    for (const sel of ['body > header', 'header', 'body > footer', 'footer']) {
      const el = document.querySelector(sel);
      if (el && visible(el) && !bands.some(b => b.contains(el) || el.contains(b))) bands.push(el);
    }
  } else {
    strategy = 'spine';
    let node = document.body, depth = 0;
    while (depth++ < 12) {
      const kids = [...node.children].filter(isBand);
      if (kids.length > 1) { bands = kids; break; }
      if (kids.length === 1) { node = kids[0]; continue; }
      // No full-bleed child: take whatever tall children exist.
      bands = [...node.children].filter(el => visible(el) && box(el).height >= opts.minHeight);
      break;
    }
  }

  bands.sort((a, b) => (box(a).top + scrollY) - (box(b).top + scrollY));

  const seen = new Set();
  const out = [];
  bands.forEach((el) => {
    const r = box(el);
    const top = Math.round(r.top + window.scrollY);
    const h = Math.round(r.height);
    const key = top + ':' + h;
    if (seen.has(key)) return;
    seen.add(key);
    // innerText reports only RENDERED text, so a section still sitting at
    // opacity:0 behind an animation gate comes back empty even though its copy
    // is fully present in the DOM. On vercel.com that hid four real sections.
    // Fall back to textContent, and record that we had to.
    let text = (el.innerText || '').replace(/\s+/g, ' ').trim();
    let hidden = false;
    if (!text) {
      const raw = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (raw) { text = raw; hidden = true; }
    }
    if (!text && !el.querySelector('img, svg, video')) return;
    out.push({
      index: out.length,
      strategy,
      tag: el.tagName.toLowerCase(),
      semantic: ['SECTION','HEADER','FOOTER','ARTICLE','ASIDE'].includes(el.tagName),
      top, height: h,
      headings: [...el.querySelectorAll('h1,h2,h3')]
        .map(x => (x.innerText || '').trim()).filter(Boolean).slice(0, 3),
      images: el.querySelectorAll('img, svg, video, picture').length,
      links: el.querySelectorAll('a').length,
      buttons: el.querySelectorAll('button, a[class*=btn], a[class*=button]').length,
      listItems: el.querySelectorAll('li').length,
      words: text.split(' ').filter(Boolean).length,
      unrendered: hidden,
      text: text.slice(0, 220),
    });
  });
  return out;
}
"""


@dataclass
class Band:
    index: int
    strategy: str
    tag: str
    semantic: bool
    top: int
    height: int
    headings: list[str]
    images: int
    links: int
    buttons: int
    listItems: int
    words: int
    unrendered: bool
    text: str
    shot: Path | None = None


@dataclass
class SiteExtract:
    url: str
    title: str
    ok: bool
    error: str = ""
    page_height: int = 0
    semantic_sections: int = 0
    bands: list[Band] = field(default_factory=list)


def extract(
    url: str,
    out_dir: Path,
    *,
    width: int = 1440,
    height: int = 900,
    min_band_height: int = 180,
    shots: bool = True,
    timeout_ms: int = 45000,
) -> SiteExtract:
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2500)
            page.evaluate(_SCROLL)
            page.wait_for_timeout(1200)
        except Exception as e:
            browser.close()
            return SiteExtract(url, "", False, f"{type(e).__name__}: {str(e)[:160]}")

        title = page.title()
        page_h = page.evaluate("document.body.scrollHeight")
        semantic = page.evaluate("document.querySelectorAll('section').length")
        raw = page.evaluate(_SEGMENT, {"minHeight": min_band_height})

        bands = [Band(**b) for b in raw]
        if shots:
            host = url.split("//")[-1].split("/")[0].replace(".", "_")
            for b in bands:
                try:
                    el = page.evaluate_handle(
                        "([t, h]) => [...document.querySelectorAll('body *')]"
                        ".find(e => { const r = e.getBoundingClientRect();"
                        " return Math.round(r.top + window.scrollY) === t"
                        " && Math.round(r.height) === h; })",
                        [b.top, b.height],
                    ).as_element()
                    if el:
                        p = out_dir / f"{host}-b{b.index:02d}.png"
                        el.screenshot(path=str(p), timeout=8000)
                        b.shot = p
                except Exception:
                    pass

        browser.close()
        return SiteExtract(url, title, True, page_height=page_h,
                           semantic_sections=semantic, bands=bands)

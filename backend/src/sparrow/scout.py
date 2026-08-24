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
    // Descend RECURSIVELY. Stopping at the first node with several band-children
    // is not enough: clerk.com yields two children of <body>, one of which is
    // 7,059px of a 7,674px page — still a wrapper, not a section. Any child that
    // dominates the page is a container, so recurse into it and keep the rest.
    const pageH = document.body.scrollHeight;
    const flatten = (node, depth) => {
      if (depth > 14) return [node];
      const kids = [...node.children].filter(isBand);
      if (!kids.length) {
        const tall = [...node.children].filter(
          el => visible(el) && box(el).height >= opts.minHeight);
        return tall.length > 1 ? tall : [node];
      }
      const out = [];
      for (const kid of kids) {
        // A child taller than 55% of the page cannot itself be one section.
        if (box(kid).height > pageH * 0.55) out.push(...flatten(kid, depth + 1));
        else out.push(kid);
      }
      return out;
    };
    bands = flatten(document.body, 0);
    // Sweep up header/footer the descent stepped over.
    for (const sel of ['body header', 'body footer']) {
      const el = document.querySelector(sel);
      if (el && visible(el) && !bands.some(b => b === el || b.contains(el))) bands.push(el);
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


# Aggregate visual register — COUNTED, never copied.
#
# The design brief carries no palettes, fonts or spacing, because blending six
# sites' aesthetics is how a page ends up looking like six sites. But that went
# too far: it also withheld whether the category has a visual convention at all.
# On a dev-tool run, two of four sources were dark-grounded and the design agent
# had no way to know, so it defaulted light. Counting "2/4 sources use a dark
# ground" is the same kind of fact as "4/4 have a hero" — convention, not taste.
_MOTION = r"""
() => {
  const anims = document.getAnimations().map(a => {
    const t = a.effect?.getTiming?.() || {};
    return {dur: Math.round(Number(t.duration) || 0), iter: t.iterations,
            name: String(a.animationName || '')};
  });
  const ambient = [...new Set(anims.filter(a => a.iter === Infinity && a.name)
    .map(a => a.name.replace(/^[\w]{4,10}_/, '').replace(/-\d+(-\d+)*/g, '')))];
  const dur = {}, ease = {}, props = {};
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (!cs.transitionDuration || cs.transitionDuration === '0s') continue;
    const d = cs.transitionDuration.split(',')[0].trim();
    const e = cs.transitionTimingFunction.split(/,(?![^(]*\))/)[0].trim();
    dur[d] = (dur[d]||0)+1; ease[e] = (ease[e]||0)+1;
    for (const p of cs.transitionProperty.split(',').map(x=>x.trim())) props[p]=(props[p]||0)+1;
  }
  const top = o => (Object.entries(o).sort((a,b)=>b[1]-a[1])[0]||[''])[0];
  const plist = Object.entries(props).sort((a,b)=>b[1]-a[1]).map(([k])=>k).slice(0,8);
  return {
    running: anims.length,
    ambient: ambient.slice(0, 6),
    tempoMs: Math.round(parseFloat(top(dur) || '0') * 1000),
    easing: top(ease),
    properties: plist,
    transform: plist.some(p => p === 'transform' || p === 'all'),
  };
}
"""


_REGISTER = r"""
() => {
  const px = (c) => { const cv=document.createElement('canvas'); cv.width=cv.height=1;
    const x=cv.getContext('2d',{willReadFrequently:true});
    x.fillStyle='#fff'; x.fillRect(0,0,1,1); x.fillStyle=c; x.fillRect(0,0,1,1);
    const d=x.getImageData(0,0,1,1).data; return [d[0],d[1],d[2]]; };
  const lum = ([r,g,b]) => (0.2126*r + 0.7152*g + 0.0722*b) / 255;
  const vw = document.documentElement.clientWidth;
  let dark = 0, light = 0;
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < vw*0.9 || r.height < 200) continue;
    const bg = getComputedStyle(el).backgroundColor;
    if (!bg || /rgba\(0, 0, 0, 0\)/.test(bg)) continue;
    (lum(px(bg)) < 0.45 ? (dark += r.height) : (light += r.height));
  }
  const body = lum(px(getComputedStyle(document.body).backgroundColor || '#fff'));
  const total = dark + light || 1;
  return {
    dark: body < 0.45 || dark/total > 0.5,
    darkShare: +(dark/total).toFixed(2),
    video: document.querySelectorAll('video').length,
    canvas: document.querySelectorAll('canvas').length,
    codeBlocks: document.querySelectorAll('pre, code').length,
    productImages: [...document.querySelectorAll('img')]
      .filter(i => i.getBoundingClientRect().width > 320).length,
  };
}
"""


@dataclass
class Motion:
    """Countable facts about how a category moves.

    The design agent was inventing motion from nothing, and the builder was
    shipping none at all. Both are evidence problems. Everything here is read
    from the live page: the Web Animations API reports what is actually running,
    and computed styles report what is declared.

    What is NOT extractable: scroll choreography driven by IntersectionObserver
    or a JS timeline. Those leave no trace in the DOM. So this measures tempo and
    register, not sequence — which is the honest limit and worth stating rather
    than papering over.
    """

    running: int                       # animations live after a scroll pass
    ambient: list[str]                 # names of infinite ones — shine, blink, drift
    tempo_ms: int                      # the dominant declared transition duration
    easing: str                        # the dominant declared easing curve
    properties: list[str]              # what is actually transitioned
    transform: bool                    # does anything move, or only recolour?


@dataclass
class Register:
    """Countable facts about how a category presents itself."""

    dark: bool
    dark_share: float
    video: int
    canvas: int
    code_blocks: int
    product_images: int
    motion: Motion | None = None


@dataclass
class SiteExtract:
    url: str
    title: str
    ok: bool
    error: str = ""
    page_height: int = 0
    semantic_sections: int = 0
    register: Register | None = None
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
        mot = page.evaluate(_MOTION)
        reg = page.evaluate(_REGISTER)
        register = Register(
            dark=bool(reg["dark"]), dark_share=float(reg["darkShare"]),
            video=int(reg["video"]), canvas=int(reg["canvas"]),
            code_blocks=int(reg["codeBlocks"]), product_images=int(reg["productImages"]),
            motion=Motion(
                running=int(mot["running"]), ambient=list(mot["ambient"]),
                tempo_ms=int(mot["tempoMs"]), easing=str(mot["easing"]),
                properties=list(mot["properties"]), transform=bool(mot["transform"]),
            ),
        )
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
                           semantic_sections=semantic, register=register, bands=bands)


# --- classification ---------------------------------------------------------

SECTION_TYPES = (
    "nav, hero, logo-wall, feature-grid, feature-detail, product-showcase, "
    "testimonial, pricing, faq, comparison, integration-grid, stats, cta, footer, other"
)

CLASSIFY_SYSTEM = f"""You label sections of a marketing website from their structure alone.

Each line gives one section: tag, pixel height, word count, and counts of images, buttons
and list items, plus its headings and the first words of its text.

Label each with exactly one of: {SECTION_TYPES}

Judge from SHAPE, not vibes:
- a logo wall is short, many images, almost no words
- a feature grid has repeated equal-weight items
- a hero is the FIRST tall band, few words, one or two buttons — position matters as much
  as shape, and a hero may carry a lot of product imagery
- a section with no words and no headings is "other". Say so rather than guessing.

JSON only: {{"labels": [{{"index": 0, "type": "...", "confidence": "high|low"}}]}}"""


def classify(provider, bands: list[Band]) -> list[str]:
    """Label bands by structure. Cheap tier, no screenshots."""
    import json as _json
    import re as _re

    from sparrow.providers import Tier

    lines = [
        f"{b.index}. <{b.tag}> h={b.height} words={b.words} imgs={b.images} "
        f"btns={b.buttons} li={b.listItems} | headings: {'; '.join(b.headings) or '-'} "
        f"| text: {b.text[:110]}"
        for b in bands
    ]
    res = provider.complete(
        tier=Tier.CHEAP, system=CLASSIFY_SYSTEM, user="\n".join(lines), max_tokens=3000
    )
    m = _re.search(r"\{.*\}", res.text, _re.DOTALL)
    if not m:
        return ["other"] * len(bands)
    out = ["other"] * len(bands)
    for lab in _json.loads(m.group(0)).get("labels", []):
        i = lab.get("index")
        if isinstance(i, int) and 0 <= i < len(out):
            out[i] = str(lab.get("type", "other"))
    return out

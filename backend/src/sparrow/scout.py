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
    # The band's own markup. Counts say a hero has 3 images and 4 buttons; the
    # markup says how they are arranged, which is the part that makes a hero
    # look like that hero. Capped because a source section can be enormous and
    # the tail of it is boilerplate.
    html: str = ""


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


# The actual colours a source paints with, weighted by how much of the page each
# covers. Counted from computed styles rather than guessed from a screenshot: a
# vision model returns a near-miss hex, and a near-miss is exactly the drift the
# design system exists to prevent.
_PALETTE = r"""
() => {
  const px = (c) => { const cv=document.createElement('canvas'); cv.width=cv.height=1;
    const x=cv.getContext('2d',{willReadFrequently:true});
    x.fillStyle='#fff'; x.fillRect(0,0,1,1); x.fillStyle=c; x.fillRect(0,0,1,1);
    const d=x.getImageData(0,0,1,1).data; return [d[0],d[1],d[2]]; };
  const hex = ([r,g,b]) => '#' + [r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('');
  const lum = ([r,g,b]) => (0.2126*r + 0.7152*g + 0.0722*b) / 255;
  const sat = ([r,g,b]) => { const M=Math.max(r,g,b), m=Math.min(r,g,b);
    return M === 0 ? 0 : (M-m)/M; };

  const area = {}, ink = {};
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    const cs = getComputedStyle(el);
    const bg = cs.backgroundColor;
    if (bg && !/rgba\(0, 0, 0, 0\)/.test(bg)) {
      const k = hex(px(bg));
      area[k] = (area[k] || 0) + r.width * r.height;
    }
    const t = (el.textContent || '').trim();
    if (t && el.children.length === 0) {
      const k = hex(px(cs.color));
      ink[k] = (ink[k] || 0) + t.length;
    }
  }
  const top = (o, n) => Object.entries(o).sort((a,b)=>b[1]-a[1]).slice(0, n)
    .map(([k,v]) => ({hex: k, weight: Math.round(v)}));

  const surfaces = top(area, 6);
  const total = surfaces.reduce((a,c)=>a+c.weight, 0) || 1;
  // The brand colour: the most-used surface that is actually saturated.
  const accent = Object.entries(area)
    .map(([k,v]) => ({hex:k, weight:v, s: sat(px(k)), l: lum(px(k))}))
    .filter(c => c.s > 0.25 && c.l > 0.06 && c.l < 0.94)
    .sort((a,b)=>b.weight-a.weight)[0] || null;

  return {
    surfaces: surfaces.map(c => ({...c, share: +(c.weight/total).toFixed(3),
                                  lum: +lum(px(c.hex)).toFixed(3)})),
    ink: top(ink, 3),
    accent: accent ? {hex: accent.hex, sat: +accent.s.toFixed(2)} : null,
    ground: hex(px(getComputedStyle(document.body).backgroundColor || '#fff')),
    ...(() => {
      // Does this page alternate section grounds, or is it one surface?
      const secs = [...document.querySelectorAll('section')].filter(s => {
        const r = s.getBoundingClientRect();
        return r.height > 200 && r.width > innerWidth * 0.9;
      });
      const g = secs.map(s => {
        let n = s, bg = 'rgba(0, 0, 0, 0)';
        while (n && /rgba\(0, 0, 0, 0\)/.test(bg)) {
          bg = getComputedStyle(n).backgroundColor; n = n.parentElement;
        }
        return hex(px(bg));
      });
      let ch = 0;
      for (let i = 1; i < g.length; i++) if (g[i] !== g[i - 1]) ch++;
      return {groundChanges: ch, distinctGrounds: new Set(g).size};
    })(),
  };
}
"""


@dataclass
class Palette:
    """What a source site is actually painted with."""

    ground: str                       # the page background, as hex
    surfaces: list[dict]              # the biggest painted areas, by share
    ink: list[dict]                   # the most-used text colours
    accent: str | None                # the most-used saturated colour
    dark: bool
    ground_changes: int = 0           # times the ground changes down the page
    distinct_grounds: int = 1         # how many grounds the page uses at all

    def swatches(self) -> list[str]:
        seen, out = set(), [self.ground]
        seen.add(self.ground)
        for c in self.surfaces:
            if c["hex"] not in seen and len(out) < 5:
                out.append(c["hex"]); seen.add(c["hex"])
        if self.accent and self.accent not in seen:
            out.append(self.accent)
        return out


# What components a category actually builds with. Our blueprints only ever asked
# for cards with an icon, a title and body text, and the pages came out uniform
# because of it. The sources use far more: kiro.dev carries 30 pills and 36
# accordions, linear.app 180 inline SVGs and 7 code blocks. None of that was ever
# measured, so the blueprinter could not ask for it.
_CENSUS = r"""
() => {
  const n = (sel) => document.querySelectorAll(sel).length;
  return {
    tabs: n('[role=tab], [role=tablist] > *'),
    accordions: n('details, [aria-expanded]'),
    pills: [...document.querySelectorAll('span,a,div,li')].filter(e => {
      const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      return r.width > 28 && r.width < 190 && r.height > 20 && r.height < 46
        && parseFloat(cs.borderRadius) > 10
        && (e.textContent || '').trim().length < 26 && !e.children.length;
    }).length,
    codeBlocks: n('pre, code'),
    tables: n('table'),
    strikethrough: [...document.querySelectorAll('*')].filter(e =>
      /line-through/.test(getComputedStyle(e).textDecorationLine)).length,
    bigNumbers: [...document.querySelectorAll('*')].filter(e =>
      !e.children.length && parseFloat(getComputedStyle(e).fontSize) > 34
      && /^[\d$€£%.,+kKmM ]{1,12}$/.test((e.textContent || '').trim())).length,
    inlineSvg: n('svg'),
  };
}
"""


@dataclass
class Components:
    """Counted component vocabulary — what this category builds pages out of."""

    tabs: int = 0
    accordions: int = 0
    pills: int = 0
    code_blocks: int = 0
    tables: int = 0
    strikethrough: int = 0
    big_numbers: int = 0
    inline_svg: int = 0

    def used(self) -> list[str]:
        names = {"tabs": self.tabs, "accordions": self.accordions, "pills": self.pills,
                 "code blocks": self.code_blocks, "tables": self.tables,
                 "strikethrough comparisons": self.strikethrough,
                 "large stat numbers": self.big_numbers,
                 "inline SVG / diagrams": self.inline_svg}
        return [f"{k} ({v})" for k, v in names.items() if v >= 2]


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

    # Arrival: measured by scrolling the page and watching what changes, rather
    # than read off the DOM at rest. The docstring above says choreography leaves
    # no trace and cannot be extracted — that is true of the SOURCE, and false of
    # the BEHAVIOUR. Sampling opacity and transform down the page recovers it:
    # antigravity.google reports 55% of elements entering from opacity 0 with a
    # 30px rise over 0.3s. Defaulted to 0 so a source that fails the pass, or an
    # extract written before this existed, simply reports nothing.
    arrival_share: float = 0.0         # fraction of elements that animate on entry
    arrival_from: float = 1.0          # median opacity they start at (1.0 = no fade)
    arrival_travel_px: int = 0         # median distance travelled on entry
    arrival_ms: int = 0                # median declared duration of those moves


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
    palette: Palette | None = None
    components: Components | None = None


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


_SETTLE = r"""
() => {
  // Put every element that is STAGED to animate into its arrived state.
  //
  // 7 of 9 bands captured from antigravity.google came back pure white
  // (stddev 0.0). That page stages 40% of its elements at opacity 0 waiting to
  // enter, `_SCROLL` did not fire them or they reverted on the way back to the
  // top, and the harness photographed a page whose content had not arrived. The
  // design director's whole-page contact sheet was a white rectangle.
  //
  // Deliberately narrow. Only elements that are transparent or offset AND
  // declare a transition — that combination is what "waiting to enter" looks
  // like. Anything hidden by display, visibility or the hidden attribute is
  // hidden on purpose: a dropdown, a dialog, an inactive tab panel. Forcing
  // those visible would produce a screenshot of a page nobody can see, which is
  // a different kind of wrong from a blank one.
  let n = 0;
  for (const el of document.querySelectorAll('*')) {
    if (el.closest('[hidden],[aria-hidden="true"],dialog:not([open])')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    // NOT gated on a declared transition. That was the first version of this
    // and it settled almost nothing: antigravity.google carries 710 elements at
    // opacity < 1 and only 86 with a CSS transition, because the motion is JS
    // writing styles frame by frame rather than transitioning. Requiring a
    // transition excluded ~90% of exactly the elements this exists to fix, and
    // the captures stayed blank — 8 of 9 bands.
    const staged = (+cs.opacity < 0.99) || (cs.transform && cs.transform !== 'none');
    if (!staged) continue;
    if (+cs.opacity < 0.99) el.style.setProperty('opacity', '1', 'important');
    if (cs.transform && cs.transform !== 'none') {
      el.style.setProperty('transform', 'none', 'important');
    }
    n++;
  }
  return n;
}
"""


_ARRIVAL = r"""
() => {
  const all = document.querySelectorAll('*');
  const staged = [];
  for (const el of all) {
    const cs = getComputedStyle(el);
    const o = +cs.opacity;
    let dy = 0;
    const m = (cs.transform || '').match(/matrix\(([^)]*)\)/);
    if (m) { const v = m[1].split(',').map(Number); dy = v[5] || 0; }
    const m3 = (cs.transform || '').match(/matrix3d\(([^)]*)\)/);
    if (m3) { const v = m3[1].split(',').map(Number); dy = v[13] || 0; }
    if (o < 0.99 || Math.abs(dy) > 1.5) {
      staged.push({o: o, dy: dy,
                   d: parseFloat((cs.transitionDuration || '').split(',')[0]) || 0});
    }
  }
  const med = a => a.length ? a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)] : 0;
  const fades = staged.filter(s => s.o < 0.99).map(s => s.o);
  const moves = staged.filter(s => Math.abs(s.dy) > 1.5 && Math.abs(s.dy) < 400)
                      .map(s => Math.abs(s.dy));
  const durs = staged.map(s => s.d).filter(x => x > 0 && x <= 3);
  return {
    share: all.length ? staged.length / all.length : 0,
    from: fades.length ? med(fades) : 1,
    travel: Math.round(med(moves)),
    ms: Math.round(med(durs) * 1000),
  };
}
"""


def _probe_arrival(page) -> dict:
    """What is STAGED to animate in, read once at load. No scrolling.

    An element waiting to enter is identifiable before it moves: it sits at
    opacity 0, or pre-offset by a transform, with a transition declared. That is
    a static fact about the page, which is why this reads it directly instead of
    watching for motion.

    Four scroll-sampling versions came before this one and every one returned a
    plausible wrong number rather than an error — 2/15 blocks, then 55% (unstable
    element identity across samples), then 19% (sampled the children of animated
    wrappers), then 8%. Sampling cannot work here: `document.getAnimations()`
    reports 8 running animations on a page that stages 755 elements, because the
    motion is JS writing styles frame by frame rather than CSS transitions, and a
    200ms sample against a 200ms move mostly catches the ends.

    Measured: antigravity.google stages 39% of its elements, fading from opacity
    0 with a 30px rise over 200ms; kiro.dev stages 4%, moving 74px over 300ms.

    Never raises: a source that will not cooperate reports nothing rather than
    failing the extract around it.
    """
    try:
        r = page.evaluate(_ARRIVAL) or {}
        return {
            "share": round(float(r.get("share", 0)), 2),
            "from": round(float(r.get("from", 1)), 2),
            "travel": int(r.get("travel", 0)),
            "ms": int(r.get("ms", 0)),
        }
    except Exception:
        return {}


def extract(
    url: str,
    out_dir: Path,
    *,
    width: int = 1440,
    height: int = 900,
    min_band_height: int = 180,
    shots: bool = True,
    timeout_ms: int = 45000,
    budget_s: int = 90,
) -> SiteExtract:
    """Extract one site, or give up inside `budget_s` and say so.

    `timeout_ms` only ever covered `page.goto`. The scroll pass and the
    segmentation evaluate had none, so a site whose JS never settles — stripe.com
    under bot detection, in practice — blocked the entire run with no error and no
    progress. A hung source is the worst failure shape available: it looks like
    slowness right up until someone gives up.

    So every step gets a timeout, and the whole call gets a wall-clock budget. A
    source that cannot be read in 90 seconds is a source the run continues without.
    """
    import time as _time

    deadline = _time.monotonic() + budget_s

    def left_ms(cap: int) -> int:
        return max(1000, min(cap, int((deadline - _time.monotonic()) * 1000)))

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
        # Every evaluate inherits this, so no single step can hang forever.
        page.set_default_timeout(left_ms(30000))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=left_ms(timeout_ms))
            page.wait_for_timeout(2500)
            page.set_default_timeout(left_ms(25000))
            # BEFORE _SCROLL, and that ordering is the whole measurement.
            # Entrances are `once: true`: they fire the first time an element
            # reaches the viewport and never again. _SCROLL exists to trigger
            # exactly that — lazy content and entrance animations — so a probe
            # running after it samples a settled page and reports a site that
            # animates half its elements as animating none. Measured: 0.55 share
            # / opacity 0.00 / 300ms before the reorder, 0.19 / 1.0 / 0ms after.
            # Order matters: the probe READS the staged state, so it has to run
            # before anything settles it; _SETTLE then puts those elements where
            # they would be once the reader arrived, so the capture is of the
            # page as seen rather than the page as loaded.
            arrival = _probe_arrival(page)
            page.evaluate(_SCROLL)
            try:
                settled = page.evaluate(_SETTLE)
            except Exception:
                settled = 0
            page.wait_for_timeout(600 if settled else 1200)
        except Exception as e:
            browser.close()
            over = _time.monotonic() >= deadline
            return SiteExtract(url, "", False,
                               f"timed out after {budget_s}s — the page never settled "
                               f"(bot protection or a JS loop)" if over
                               else f"{type(e).__name__}: {str(e)[:160]}")

        try:
            page.set_default_timeout(left_ms(20000))
            title = page.title()
            page_h = page.evaluate("document.body.scrollHeight")
            semantic = page.evaluate("document.querySelectorAll('section').length")
            cen = page.evaluate(_CENSUS)
            mot = page.evaluate(_MOTION)
            arr = arrival
            pal = page.evaluate(_PALETTE)
            reg = page.evaluate(_REGISTER)
        except Exception as e:
            browser.close()
            return SiteExtract(url, "", False,
                               f"unreadable after load: {type(e).__name__}: {str(e)[:120]}")
        register = Register(
            dark=bool(reg["dark"]), dark_share=float(reg["darkShare"]),
            video=int(reg["video"]), canvas=int(reg["canvas"]),
            code_blocks=int(reg["codeBlocks"]), product_images=int(reg["productImages"]),
            palette=Palette(
                ground=str(pal["ground"]), surfaces=list(pal["surfaces"]),
                ink=list(pal["ink"]),
                accent=(pal["accent"] or {}).get("hex"),
                dark=bool(reg["dark"]),
                ground_changes=int(pal.get("groundChanges", 0)),
                distinct_grounds=int(pal.get("distinctGrounds", 1)),
            ),
            components=Components(
                tabs=int(cen["tabs"]), accordions=int(cen["accordions"]),
                pills=int(cen["pills"]), code_blocks=int(cen["codeBlocks"]),
                tables=int(cen["tables"]), strikethrough=int(cen["strikethrough"]),
                big_numbers=int(cen["bigNumbers"]), inline_svg=int(cen["inlineSvg"]),
            ),
            motion=Motion(
                running=int(mot["running"]), ambient=list(mot["ambient"]),
                tempo_ms=int(mot["tempoMs"]), easing=str(mot["easing"]),
                properties=list(mot["properties"]), transform=bool(mot["transform"]),
                arrival_share=float(arr.get("share", 0.0)),
                arrival_from=float(arr.get("from", 1.0)),
                arrival_travel_px=int(arr.get("travel", 0)),
                arrival_ms=int(arr.get("ms", 0)),
            ),
        )
        try:
            page.set_default_timeout(left_ms(20000))
            raw = page.evaluate(_SEGMENT, {"minHeight": min_band_height})
        except Exception as e:
            browser.close()
            return SiteExtract(url, title, False,
                               f"segmentation failed: {type(e).__name__}: {str(e)[:120]}")

        bands = [Band(**b) for b in raw]
        host = url.split("//")[-1].split("/")[0].replace(".", "_")
        for b in bands:
            if _time.monotonic() >= deadline:
                break                       # keep the bands, drop the extras
            try:
                el = page.evaluate_handle(
                    "([t, h]) => [...document.querySelectorAll('body *')]"
                    ".find(e => { const r = e.getBoundingClientRect();"
                    " return Math.round(r.top + window.scrollY) === t"
                    " && Math.round(r.height) === h; })",
                    [b.top, b.height],
                ).as_element()
                if not el:
                    continue
                # Markup always. It is one evaluate on a handle already in hand,
                # and it is the only record of how the section is ARRANGED —
                # everything else about a band is a count.
                b.html = (el.evaluate("e => e.outerHTML") or "")[:14000]
                if shots:
                    # Scroll it into view and WAIT before shooting. Entrances on
                    # these pages are driven by a JS loop that rewrites inline
                    # styles every frame, so forcing opacity statically loses the
                    # next tick — 8 of 9 antigravity bands stayed blank with the
                    # override in place. Working with the animation instead of
                    # against it: put the band on screen, let its entrance play,
                    # then capture what a reader would actually see.
                    try:
                        el.scroll_into_view_if_needed(timeout=4000)
                        page.wait_for_timeout(700)
                    except Exception:
                        pass
                    dest = out_dir / f"{host}-b{b.index:02d}.png"
                    el.screenshot(path=str(dest), timeout=8000)
                    b.shot = dest
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

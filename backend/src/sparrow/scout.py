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
    // How wide the band's CONTENT actually sits, as a fraction of the viewport.
    // The band itself is nearly always full width; what varies — and what a
    // reader sees — is how far the things inside it span. Measured on
    // elevenlabs.io/creative: 0.36 for a logo strip, 0.75 for the common
    // column, 0.94 for a product band. Every page this harness builds is
    // max-w-6xl, a flat 0.80 for every section, which is why they read as
    // clustered in the middle: near the average of a real page and never near
    // its extremes. Clamped to the viewport because a horizontal carousel runs
    // far past the right edge and its true width is what can be seen.
    // `counted`, not `seen`: an earlier version called this `seen` and shadowed
    // the outer `const seen = new Set()` used for de-duplication a few lines
    // up. `let` hoists into a temporal dead zone across the whole block, so
    // `seen.has(key)` ABOVE this line began throwing, the evaluate failed, and
    // segmentation returned zero bands for every site.
    let lo = Infinity, hi = -Infinity, counted = 0;
    let cTop = Infinity, cBot = -Infinity;
    const bandRect = el.getBoundingClientRect();
    for (const c of el.querySelectorAll('h1,h2,h3,p,img,video,li,button,svg')) {
      const cr = c.getBoundingClientRect();
      if (cr.width < 24 || cr.height < 12) continue;
      const left = Math.max(cr.left, 0), right = Math.min(cr.right, window.innerWidth);
      if (right <= left) continue;
      lo = Math.min(lo, left); hi = Math.max(hi, right); counted++;
      cTop = Math.min(cTop, cr.top); cBot = Math.max(cBot, cr.bottom);
    }
    const span = counted ? Math.round(hi - lo) : 0;
    // Where the content sits INSIDE the band. Every page this harness built
    // centred its content in every section — 128px above, 128px below, six
    // times over — because the only vertical vocabulary it had was `py-*`,
    // which is symmetric by definition, and nothing ever measured that the
    // sources do otherwise: deepseek puts a section's content in its top 15%
    // and leaves 822px of ground under it; antigravity pins one to the bottom
    // with 4px to spare. Reported as the two paddings so the composer can see
    // the void, not just the height.
    const padTop = counted ? Math.round(cTop - bandRect.top) : 0;
    const padBot = counted ? Math.round(bandRect.bottom - cBot) : 0;

    // HOW THIS BAND SEPARATES ITS CONTENT. Every page this harness built put
    // its content in boxes — rounded-lg border border-border bg-card, nine
    // times in one section — and the sources it was built from put theirs in
    // none: sarvam separates with a gradient wash and whitespace, elevenlabs
    // with air. The scout measured palette, type, canvas and video and never
    // this, so the design agent had no evidence the category does not box
    // things, and the prior filled the gap with the one container the stack
    // ships. Counted over the band's visible block-level elements: enclosed
    // means a visible border, a box-shadow, or a fill that differs from the
    // band's own ground.
    const bandBg = getComputedStyle(el).backgroundColor;
    // The band's EFFECTIVE ground — its own fill, or the nearest painted
    // ancestor's when it is transparent — as hex and luminance, next to the
    // page's. The register already counts how many grounds a page uses; what
    // it never said is WHICH band sits on the other one, so the composer read
    // "2 grounds, 3 changes" and had nothing to place. Measured on sarvam: a
    // full-bleed dark band under the headline at band 6, and every page built
    // from it on one pale ground end to end.
    const effBg = (n) => {
      let bg = 'rgba(0, 0, 0, 0)';
      while (n && /rgba\(\d+, \d+, \d+, 0\)|transparent/.test(bg)) {
        bg = getComputedStyle(n).backgroundColor; n = n.parentElement;
      }
      return bg;
    };
    const toRgb = (c) => ((c || '').match(/[\d.]+/g) || [255, 255, 255]).slice(0, 3).map(Number);
    const toHex = (c) => '#' + toRgb(c).map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
    const toLum = (c) => { const [r, g, b] = toRgb(c); return +((0.2126*r + 0.7152*g + 0.0722*b) / 255).toFixed(3); };
    const groundCss = effBg(el);
    const pageCss = effBg(document.body);
    const groundHex = toHex(groundCss), pageHex = toHex(pageCss);
    // Is there a large painted layer INSIDE the band that is not its ground —
    // an image, video, canvas or gradient covering most of it? That is a band
    // whose ground is a picture, which no colour token can say.
    let layered = false;
    for (const c of el.querySelectorAll('canvas, video, img, picture, div')) {
      const r = c.getBoundingClientRect();
      if (r.width < innerWidth * 0.6 || r.height < h * 0.6) continue;
      const cs = getComputedStyle(c);
      if (c.tagName !== 'DIV' || /gradient|url\(/.test(cs.backgroundImage)) { layered = true; break; }
    }
    let blocks = 0, bordered = 0, shadowed = 0, filled = 0, rounded = 0, rules = 0;
    for (const c of el.querySelectorAll('div,section,article,li,figure,a,button')) {
      const r = c.getBoundingClientRect();
      if (r.width < 80 || r.height < 40) continue;
      const cs = getComputedStyle(c);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      blocks++;
      const bw = ['Top','Right','Bottom','Left'].map(s => parseFloat(cs['border'+s+'Width']) || 0);
      const visibleBorder = bw.some(w => w > 0) && !/rgba\(\d+, \d+, \d+, 0\)|transparent/.test(cs.borderTopColor);
      const allSides = bw.every(w => w > 0);
      if (visibleBorder && allSides) bordered++;
      else if (visibleBorder) rules++;            // a hairline on one edge is a rule, not a box
      if (cs.boxShadow && cs.boxShadow !== 'none') shadowed++;
      const bg = cs.backgroundColor;
      if (bg && !/rgba\(\d+, \d+, \d+, 0\)|transparent/.test(bg) && bg !== bandBg) filled++;
      if ((parseFloat(cs.borderTopLeftRadius) || 0) >= 6) rounded++;
    }
    const enclosed = blocks ? +(((bordered + shadowed) / blocks)).toFixed(3) : 0;
    // The SURFACE VOCABULARY: how many distinct radii and shadows this band
    // actually uses. The design system records one card radius and two shadows
    // and the audit punishes anything else — so every container on every page
    // built here had the same corner and the same shadow, and the page read as
    // one shape stamped thirty times. Sources use five radii because they have
    // five kinds of surface. Counted here so the designer can record a scale
    // sized like the source's, the way type already is.
    const radii = new Set(), shadows = new Set();
    for (const c of el.querySelectorAll('div,section,article,li,figure,a,button,img,video')) {
      const r = c.getBoundingClientRect(); if (r.width < 40 || r.height < 24) continue;
      const cs = getComputedStyle(c);
      const rad = Math.round(parseFloat(cs.borderTopLeftRadius) || 0);
      if (rad > 0) radii.add(rad >= 999 ? 'full' : rad);
      if (cs.boxShadow && cs.boxShadow !== 'none') shadows.add(cs.boxShadow.replace(/rgba?\([^)]*\)/g, 'c').slice(0, 60));
    }

    out.push({
      index: out.length,
      strategy,
      tag: el.tagName.toLowerCase(),
      semantic: ['SECTION','HEADER','FOOTER','ARTICLE','ASIDE'].includes(el.tagName),
      contentWidth: span,
      contentShare: counted ? +(span / window.innerWidth).toFixed(2) : 0,
      inset: counted ? Math.round(Math.min(lo, window.innerWidth - hi)) : 0,
      padTop, padBot,
      ground: {hex: groundHex, lum: toLum(groundCss), page: pageHex,
               differs: groundHex !== pageHex, layered},
      enclosure: {blocks, bordered, shadowed, filled, rounded, rules, enclosed,
                  radii: [...radii].sort((a,b)=>(a==='full')-(b==='full')||a-b), shadows: [...shadows]},
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
    # Measured, not chosen from a vocabulary. An earlier version of this had the
    # composition pass pick from contained/wide/full-bleed — three words I
    # invented, which cannot express the 0.36, 0.47, 0.57 and 0.64 a real page
    # actually uses.
    contentWidth: int
    contentShare: float
    inset: int
    # Content's distance from the band's top and bottom edges. Equal means
    # centred; a large padBot with a small padTop is content pinned high over
    # a void — the thing `py-*` cannot express and the sources do constantly.
    padTop: int
    padBot: int
    # How the band separates its content: counts of visible blocks that are
    # bordered on all sides, shadowed, filled against the ground, rounded, or
    # ruled on one edge — and `enclosed`, the share that are boxed at all.
    enclosure: dict
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
    # What the band sits on: {hex, lum, page, differs, layered}. `differs` is
    # this band against the page ground; `layered` is a picture, canvas, video
    # or gradient covering most of the band — a ground no colour token names.
    ground: dict = field(default_factory=dict)


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
    // WHAT the video is, not just how many. A count cannot tell ambient
    // background footage from a demo you press play on, and those want opposite
    // treatments — one is texture behind a section, the other is the section.
    // muted+loop+autoplay together is the signature of decoration; controls is
    // the signature of content.
    videos: [...document.querySelectorAll('video')].slice(0, 6).map(v => {
      const r = v.getBoundingClientRect();
      return {
        w: Math.round(r.width), h: Math.round(r.height),
        bleed: r.width >= window.innerWidth * 0.92,
        muted: v.muted || v.hasAttribute('muted'),
        loop: v.loop || v.hasAttribute('loop'),
        autoplay: v.autoplay || v.hasAttribute('autoplay'),
        controls: v.controls || v.hasAttribute('controls'),
        poster: v.getAttribute('poster') || '',
        secs: Number.isFinite(v.duration) ? Math.round(v.duration) : 0,
      };
    }),
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
# The count said 62 inline SVGs and nothing about what any of them draws. A
# number cannot be reproduced: `inline_svg: 62` tells the builder this category
# likes diagrams, not what a diagram here looks like. So keep the markup of the
# largest few — SVG is small, it is source code, and it is the only record of
# how this category draws the thing it cannot photograph. `animated` matters
# separately: a static diagram and a looping one are different components with
# the same tag, and the harness has never been able to tell them apart.
_SVGS = r"""
() => [...document.querySelectorAll('svg')]
  .map(s => ({ s, r: s.getBoundingClientRect() }))
  .filter(({ r }) => r.width >= 48 && r.height >= 48)
  .sort((a, b) => b.r.width * b.r.height - a.r.width * a.r.height)
  .slice(0, 6)
  .map(({ s, r }) => ({
    w: Math.round(r.width), h: Math.round(r.height),
    top: Math.round(r.top + window.scrollY),
    viewBox: s.getAttribute('viewBox') || '',
    nodes: s.querySelectorAll('path,circle,rect,line,polyline,polygon,ellipse').length,
    // SMIL, CSS animation, or a CSS transition with a real duration. Any of the
    // three means it moves; none of them means it is a drawing.
    animated: !!s.querySelector('animate,animateTransform,animateMotion') ||
      [...s.querySelectorAll('*')].some(e => {
        const cs = getComputedStyle(e);
        return (cs.animationName && cs.animationName !== 'none') ||
               parseFloat(cs.transitionDuration || '0') > 0;
      }),
    markup: s.outerHTML.slice(0, 2400),
  }))
"""


# What the page sets its type in. Measured, because the design director never
# knew: it saw palette, dark share, motion tempo — and picked a face from its
# prior every time. Across every project built, that prior was Space Grotesk.
# antigravity.google is set in Google Sans at 80px centred; deepseek's harness
# page in a tight geometric at 46px. Neither fact ever reached the agent that
# chooses type, so it could not choose in the source's register even when it
# wanted to. This is the same shape as the palette probe: read the computed
# styles of the elements that carry the page's voice, report them as evidence.
_TYPE = r"""
() => {
  const pick = (sel) => {
    const els = [...document.querySelectorAll(sel)].filter(e => {
      const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (e.innerText||'').trim();
    });
    if (!els.length) return null;
    // the biggest one on the page, not the first in the DOM
    els.sort((a, b) => parseFloat(getComputedStyle(b).fontSize) - parseFloat(getComputedStyle(a).fontSize));
    const e = els[0], cs = getComputedStyle(e), r = e.getBoundingClientRect();
    const fam = (cs.fontFamily || '').split(',')[0].replace(/["']/g, '').trim();
    return {
      family: fam, weight: cs.fontWeight, size: Math.round(parseFloat(cs.fontSize)),
      lineHeight: +(parseFloat(cs.lineHeight) / parseFloat(cs.fontSize)).toFixed(2) || null,
      tracking: cs.letterSpacing === 'normal' ? 0 : +(parseFloat(cs.letterSpacing) / parseFloat(cs.fontSize)).toFixed(3),
      transform: cs.textTransform, align: cs.textAlign,
      // where it sits: a centred hero headline and a left-aligned one are
      // different pages
      x: +((r.left + r.width / 2) / window.innerWidth).toFixed(2),
    };
  };
  const body = pick('p');
  return {
    display: pick('h1'),
    heading: pick('h2'),
    body,
    mono: (() => {
      const e = document.querySelector('code, pre, kbd');
      if (!e) return null;
      return (getComputedStyle(e).fontFamily || '').split(',')[0].replace(/["']/g, '').trim();
    })(),
    // how many distinct families the page actually loads — one is a system,
    // four is a mess
    families: [...new Set([...document.querySelectorAll('h1,h2,h3,p,a,button,li')]
      .map(e => (getComputedStyle(e).fontFamily || '').split(',')[0].replace(/["']/g, '').trim())
      .filter(Boolean))].slice(0, 6),
  };
}
"""


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
    # Per-video facts, up to six. `video: 3` says a category uses video; these
    # say whether it is texture or content, which is the only version of that
    # fact a design agent can act on.
    videos: list[dict] = field(default_factory=list)
    # The largest few inline SVGs, with their markup and whether they move.
    svgs: list[dict] = field(default_factory=list)
    # The faces, sizes and alignment the page sets its voice in. See _TYPE.
    typography: dict = field(default_factory=dict)
    # A frame of each large <canvas>, with its rect and band. `canvas: 4` said
    # antigravity draws something; it could not say a particle field of
    # coloured dashes drifting across a pale ground — the one thing on that
    # page a visitor remembers. Same blindness video had, same fix.
    canvases: list[dict] = field(default_factory=list)
    # Back-reference to the bands this register was measured over, set by the
    # caller. `register_report` sums enclosure across them.
    _bands: list = field(default_factory=list, repr=False, compare=False)
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


_DISMISS = r"""
() => {
  // Consent dialogs, chat launchers and region banners arrive with the VISIT,
  // not with the design, and they sit on top of the page in every screenshot
  // this harness takes. The reader duly described elevenlabs' privacy panel as
  // a page feature and explained how to build one; the design director and the
  // builder have been looking at it all along without anyone noticing.
  //
  // Accept is clicked rather than the dialog hidden, where an accept exists: a
  // hidden dialog often leaves the page scroll-locked behind it, and a page
  // that cannot scroll segments into one enormous band.
  const WORDS = /cookie|consent|privacy|gdpr|tracking/i;
  const OK = /^(accept|allow|agree|got it|ok|i agree|accept all|allow all)\b/i;
  let clicked = 0, hidden = 0;

  for (const el of document.querySelectorAll('div,section,aside,dialog,[role="dialog"]')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 120 || r.height < 60) continue;
    const txt = (el.innerText || '').slice(0, 400);
    if (!WORDS.test(txt) && !WORDS.test(el.className || '') && !WORDS.test(el.id || '')) continue;
    const btn = [...el.querySelectorAll('button,a[role="button"],[role="button"]')]
      .find(b => OK.test((b.innerText || '').trim()));
    if (btn) { btn.click(); clicked++; }
    else { el.style.setProperty('display', 'none', 'important'); hidden++; }
  }

  // ANY full-viewport overlay, whatever it says. The keyword pass above only
  // knows consent dialogs; deepseek.com loaded with its navigation drawer
  // open — four links on a black sheet, no cookie word anywhere — and every
  // one of its nine band screenshots was that sheet. It was then ranked the
  // primary reference, and a whole site was designed dark off a hamburger
  // menu. Escape closes most drawers; a close control closes the rest; hiding
  // is the last resort and the same fallback the consent pass uses.
  const vw = window.innerWidth, vh = window.innerHeight;
  let overlays = 0;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed') continue;
    const r = el.getBoundingClientRect();
    if (r.width < vw * 0.85 || r.height < vh * 0.85) continue;
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.5) continue;
    if (cs.pointerEvents === 'none') continue;           // a decorative layer
    // A PINNED HERO IS ALSO FIXED AND FULL-VIEWPORT. antigravity.google keeps
    // its whole opening section in a fixed 1440x900 div, and the first version
    // of this pass display:none'd it — the document collapsed from 10029px to
    // 900px and the capture was a nav bar over white. What separates a hero
    // from a sheet is what is IN it: a headline, not a list of links. So an
    // element carrying a heading is never touched, and nothing is ever hidden
    // outright — a close control is clicked if there is one, Escape is sent,
    // and a sheet that survives both is left for the blank-capture guard.
    if (el.querySelector('h1,h2')) continue;
    const close = [...el.querySelectorAll('button,[role="button"],a')].find(b =>
      /close|dismiss|menu/i.test(b.getAttribute('aria-label') || '') ||
      /^[×✕✖xX]$/.test((b.innerText || '').trim()));
    if (close) { close.click(); overlays++; }
  }
  document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));

  // Whatever the dialog did to the scroll while it was up.
  for (const n of [document.documentElement, document.body]) {
    n.style.removeProperty('overflow');
    n.style.removeProperty('position');
  }
  return {clicked, hidden, overlays};
}
"""


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
    // A CLOSED OVERLAY IS NOT A STAGED ENTRANCE. deepseek.com keeps its mobile
    // menu at opacity 0 with pointer-events none until a button opens it. This
    // pass saw opacity 0, called it "waiting to enter", set it to 1 — and a
    // full-viewport black sheet with four links dropped over the page. Every
    // band screenshot after that was the sheet, it ranked as the primary
    // reference, and a site was designed dark off a menu the harness itself had
    // opened. An entrance animation never disables its own pointer events;
    // a drawer that is closed always does.
    if (cs.position === 'fixed' && cs.pointerEvents === 'none') continue;
    if (cs.position === 'fixed') {
      const r = el.getBoundingClientRect();
      if (r.width >= innerWidth * 0.85 && r.height >= innerHeight * 0.85) continue;
    }
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


# Titles a bot wall or a network filter serves INSTEAD of the site. Measured on
# two independent cases in one afternoon: unity.com behind Akamai answered
# headless Chromium with a 1-band "Access Denied", and an office Sophos filter
# answered every gaming domain with a 1-band "Blocked site" — and `extract`
# reported ok=True for both, handing a design brief a page that was an error
# screen. A run built on that looks like a success the whole way through.
_BLOCK_TITLES = (
    "access denied", "blocked site", "just a moment", "attention required",
    "403 forbidden", "pardon our interruption", "are you a robot",
    "security check", "request blocked",
)


def _blocked(title: str, sections: int, height: int) -> bool:
    """A wall, not a page. Title is the reliable signal; the rest is corroboration."""
    low = (title or "").strip().lower()
    if any(b in low for b in _BLOCK_TITLES):
        return True
    # No title at all AND nothing structural AND barely taller than the viewport.
    return not low and sections == 0 and height <= 1000



def _extract_once(
    url: str,
    out_dir: Path,
    *,
    width: int = 1440,
    height: int = 900,
    min_band_height: int = 180,
    shots: bool = True,
    timeout_ms: int = 45000,
    budget_s: int = 90,
    headed: bool = False,
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
        # Headed defeats the bot walls headless trips. Measured on unity.com:
        # headless got "Access Denied" with 0 sections, headed got the real page
        # with 23 sections and a video. Not the default — headed needs a display
        # and is slower — so it is what the retry below escalates to.
        browser = pw.chromium.launch(
            headless=not headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
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
            # Before the settling scroll, so the page that gets scrolled,
            # measured and photographed is the page without the overlay.
            try:
                page.evaluate(_DISMISS)
                page.wait_for_timeout(400)
            except Exception:
                pass
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
            if _blocked(title, semantic, page_h):
                browser.close()
                # Marker, not a retry. `extract` below re-enters headed; doing it
                # here would nest sync_playwright inside its own context, which
                # raises instead of retrying.
                return SiteExtract(url, title, False, f"{_BLOCKED_MARK}{title}")
            cen = page.evaluate(_CENSUS)
            mot = page.evaluate(_MOTION)
            arr = arrival
            pal = page.evaluate(_PALETTE)
            reg = page.evaluate(_REGISTER)
            svgs = page.evaluate(_SVGS)
            try:
                typo = page.evaluate(_TYPE)
            except Exception:
                typo = {}
        except Exception as e:
            browser.close()
            return SiteExtract(url, "", False,
                               f"unreadable after load: {type(e).__name__}: {str(e)[:120]}")
        register = Register(
            dark=bool(reg["dark"]), dark_share=float(reg["darkShare"]),
            video=int(reg["video"]), videos=list(reg.get("videos") or []),
            svgs=list(svgs or []),
            typography=dict(typo or {}),
            canvas=int(reg["canvas"]),
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
        # "Differs" against the ground MOST of the page sits on, not against
        # <body>'s colour: gnani paints body #f9fafb and every band #ffffff, so
        # measured against body every band "differed" and the two cream bands
        # that actually change register were indistinguishable from the rest.
        weight: dict[str, int] = {}
        for b in bands:
            hx = (b.ground or {}).get("hex")
            if hx and not (b.ground or {}).get("layered"):
                weight[hx] = weight.get(hx, 0) + max(b.height, 1)
        if weight:
            page_hex = max(weight, key=weight.get)
            for b in bands:
                if b.ground:
                    b.ground["page"] = page_hex
                    b.ground["differs"] = b.ground.get("hex") != page_hex
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

        # A FRAME OF THE SOURCE'S OWN VIDEO. Everything the harness knew about a
        # source video was adjectives — muted, looping, 20s, full-bleed — and you
        # cannot generate footage that resembles a thing from its adjectives. The
        # frame is free: Playwright renders video into a screenshot, so the band
        # shot already contained one and nothing ever isolated it. Shot off the
        # element rather than cropped out of the band, because the band shot is
        # scaled and the crop maths is one more thing to get wrong.
        #
        # Matched back to a band by document position, so the placement pass can
        # ask "what did the source put AROUND its video" and not just "was there
        # one".
        if register.videos:
            for i, el in enumerate(page.query_selector_all("video")[:6]):
                if i >= len(register.videos) or _time.monotonic() >= deadline:
                    break
                try:
                    el.scroll_into_view_if_needed(timeout=3000)
                    # MAKE IT PLAY, THEN WAIT FOR A REAL FRAME. A fixed 900ms was
                    # enough for vapi and cryengine and produced pure white for
                    # both of antigravity's loops and near-black for deepseek's:
                    # lazy-loaded video has no frame to show until it is asked
                    # to play and has buffered one. The curator then read a
                    # blank frame, honestly reported "a uniform near-white field
                    # with no discernible subject", and generated stock footage
                    # from nothing — a woman at three monitors.
                    try:
                        el.evaluate("v => { v.muted = true; return v.play(); }")
                    except Exception:
                        pass
                    ready = False
                    for _ in range(12):                 # up to ~4.8s
                        page.wait_for_timeout(400)
                        try:
                            ready = bool(el.evaluate(
                                "v => v.readyState >= 2 && !v.paused && v.currentTime > 0.25"))
                        except Exception:
                            ready = False
                        if ready:
                            break
                    box = el.bounding_box()
                    dest = out_dir / f"{host}-v{i:02d}.png"
                    # DRAW THE FRAME, DON'T SCREENSHOT THE ELEMENT. Chromium keeps
                    # a playing video on its own compositor layer, and the element
                    # screenshot does not always include it: antigravity's hero
                    # loop came back pure white from el.screenshot() while the
                    # same element, drawn to a canvas, gave the real title card.
                    # Same-origin video draws cleanly; a cross-origin one taints
                    # the canvas and toDataURL throws, so fall back to the shot.
                    grabbed = False
                    try:
                        data_url = el.evaluate(
                            """v => { const c = document.createElement('canvas');
                                   c.width = v.videoWidth; c.height = v.videoHeight;
                                   c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
                                   return c.toDataURL('image/png'); }""")
                        if isinstance(data_url, str) and data_url.startswith("data:image/png;base64,"):
                            import base64 as _b64
                            dest.write_bytes(_b64.b64decode(data_url.split(",", 1)[1]))
                            grabbed = dest.stat().st_size > 2048
                    except Exception:
                        grabbed = False
                    if not grabbed:
                        el.screenshot(path=str(dest), timeout=8000)
                    # And never file a blank one — no frame is better than a frame
                    # of nothing, because downstream cannot tell the difference.
                    if not _frame_has_content(dest):
                        dest.unlink(missing_ok=True)
                        register.videos[i]["frame"] = None
                        register.videos[i]["frame_note"] = "blank at capture"
                    else:
                        register.videos[i]["frame"] = str(dest)
                    if box:
                        top = int(box["y"] + page.evaluate("window.scrollY"))
                        register.videos[i]["top"] = top
                        register.videos[i]["band"] = next(
                            (b.index for b in bands
                             if b.top <= top < b.top + b.height), None)
                        # Is the copy ON it, or beside it. Measured for canvas
                        # already; a video the headline sits on is the page's
                        # atmosphere, one in a card beside the copy is an object.
                        # Which one it is decides what role a generated loop can
                        # play, and that decision belongs downstream.
                        try:
                            register.videos[i]["under_heading"] = bool(page.evaluate(
                                """(el) => { const r = el.getBoundingClientRect();
                                   return [...document.querySelectorAll('h1,h2')].some(h => {
                                     const q = h.getBoundingClientRect();
                                     return q.left >= r.left - 4 && q.right <= r.right + 4
                                         && q.top >= r.top - 4 && q.bottom <= r.bottom + 4; }); }""",
                                el))
                        except Exception:
                            register.videos[i]["under_heading"] = False
                except Exception:
                    pass

        # A FRAME OF EACH LARGE CANVAS. The scout has counted canvases since the
        # register existed and never looked at one. A canvas is where a page
        # keeps the thing it cannot express as markup — a particle field, a
        # generative texture, a WebGL scene — and a count of them tells the
        # designer nothing it can invent a treatment from.
        if register.canvas:
            n = 0
            for el in page.query_selector_all("canvas"):
                if n >= 4 or _time.monotonic() >= deadline:
                    break
                try:
                    box = el.bounding_box()
                    if not box or box["width"] < 240 or box["height"] < 160:
                        continue
                    el.scroll_into_view_if_needed(timeout=3000)
                    page.wait_for_timeout(700)      # let it draw a few frames
                    dest = out_dir / f"{host}-c{n:02d}.png"
                    el.screenshot(path=str(dest), timeout=8000)
                    # DOES IT MOVE. A still of a particle field and a still of a
                    # painted texture look the same; the pages do not. Shoot it
                    # again half a second later and measure the change — a live
                    # loop differs frame to frame, a static drawing does not.
                    # Without this the director knew the source HAD an ambient
                    # layer and wrote a static gradient for it every time.
                    page.wait_for_timeout(500)
                    again = el.screenshot(timeout=8000)
                    live = _frames_differ(dest.read_bytes(), again)
                    top = int(box["y"] + page.evaluate("window.scrollY"))
                    band_ix = next((b.index for b in bands
                                    if b.top <= top < b.top + b.height), None)
                    register.canvases.append({
                        "w": int(box["width"]), "h": int(box["height"]),
                        "bleed": box["width"] >= width * 0.92,
                        "top": top, "frame": str(dest), "live": live,
                        "band": band_ix,
                        # Behind copy, or beside it? A field the headline sits
                        # on is the page's atmosphere; one in a card is a picture.
                        "under_heading": bool(page.evaluate(
                            """(el) => { const r = el.getBoundingClientRect();
                               return [...document.querySelectorAll('h1,h2')].some(h => {
                                 const q = h.getBoundingClientRect();
                                 return q.left >= r.left - 4 && q.right <= r.right + 4
                                     && q.top >= r.top - 4 && q.bottom <= r.bottom + 4; }); }""",
                            el)),
                    })
                    n += 1
                except Exception:
                    pass

        browser.close()
        return SiteExtract(url, title, True, page_height=page_h,
                           semantic_sections=semantic, register=register, bands=bands)



def _frame_has_content(path: Path) -> bool:
    """Is there anything in this picture.

    Edge density alone is not enough for footage: antigravity's title card —
    a black field, a wordmark, sparse coloured dashes — measures 1.6% edges,
    the same as a sheet of pure white. What separates them is tonal range: a
    blank capture has one luminance level, real footage has dozens. Either
    signal is sufficient; a frame needs both to fail before it is thrown out.
    """
    try:
        from PIL import Image, ImageFilter
        with Image.open(path) as im:
            L = im.convert("L")
            e = L.resize((256, 256)).filter(ImageFilter.FIND_EDGES).tobytes()
            levels = len(set(L.resize((96, 96)).tobytes()))
        edges = sum(1 for x in e if x > 40) / len(e)
        return edges >= 0.03 or levels >= 24
    except Exception:
        return True                      # cannot tell: keep it


def _frames_differ(a: bytes, b: bytes, threshold: float = 0.02) -> bool:
    """Did a canvas change between two shots half a second apart?

    Mean absolute pixel difference on a 64x64 downsample, measured at the
    scout's own device_scale_factor=2 — the DPR matters, because the same
    drift reads 1.2 at 1x and 0.14 at 2x once the downsample averages four
    times the pixels. At 2x: a static drawing shot twice is exactly 0.000
    (PNG is lossless); antigravity's slowly drifting particle field 0.139; a
    slow shimmer 0.057; deepseek's hero orbs 5-11. Two earlier thresholds
    (1.5, then 0.5) were set from 1x measurements and called every canvas
    static inside the real scout. 0.02 sits above nothing and below the
    slowest motion seen.
    """
    try:
        import io
        from PIL import Image, ImageChops
        x = Image.open(io.BytesIO(a)).convert("L").resize((64, 64))
        y = Image.open(io.BytesIO(b)).convert("L").resize((64, 64))
        px = ImageChops.difference(x, y).tobytes()
        return (sum(px) / len(px)) > threshold
    except Exception:
        return False


def _blank_share(bands: list[Band]) -> float:
    """What fraction of the band screenshots are pictures of nothing — and
    mark each one so the ranker sees it.

    A screenshot with no edges in it is not a section; it is something sitting
    over the section, or a section that never painted. Measured on one run:
    deepseek.com loaded with its navigation drawer open, so all nine bands were
    a black sheet with four links — and it was ranked the primary reference,
    and a site was designed dark off a hamburger menu. On the same run four of
    antigravity's six bands were pure white: entrances that never arrived.

    Edge density is the signal, not brightness or variance. Both walls above
    score under 2%; every real band on the same run scores over 5%, including
    the airy light ones that variance alone had flagged as blank.

    A band judged blank is marked `unrendered`, which the ranking line already
    prints as "TEXT NOT RENDERED" — the existing DOM-side hint, now backed by
    the pixels. The caller decides whether the whole site is a wall.
    """
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return 0.0
    shot = [b for b in bands if b.shot and b.shot.is_file()]
    if not shot:
        return 0.0
    blank = 0
    for b in shot:
        try:
            with Image.open(b.shot) as im:
                edges = im.convert("L").resize((256, 256)).filter(ImageFilter.FIND_EDGES)
                px = edges.tobytes()
        except OSError:
            continue
        density = sum(1 for x in px if x > 40) / len(px)
        if density < 0.03:
            b.unrendered = True
            blank += 1
    return blank / len(shot)


_BLOCKED_MARK = "blocked:"


def extract(url: str, out_dir: Path, **kw) -> SiteExtract:
    """Extract one site, escalating to a headed browser if a wall answers first.

    Two separate walls produce the same useless result — an Akamai bot check and
    an office web filter both serve a short page with a title like "Access
    Denied", and the old `extract` reported it as a successful read. Headed
    defeats the first (measured on unity.com: 0 sections headless, 23 headed)
    and cannot defeat the second, so a still-blocked retry fails loudly instead
    of handing the run an error screen to design from.
    """
    r = _extract_once(url, out_dir, **kw)
    # A read that succeeded on every count and produced pictures of nothing is
    # a wall too. Retry headed like a block page: a drawer that opened on a
    # headless visit often does not on a headed one, and if it does again the
    # loud failure is still better than a dark site designed off a menu.
    if r.ok and kw.get("shots", True) and _blank_share(r.bands) >= 0.85:
        r = SiteExtract(url, r.title, False,
                        f"{_BLOCKED_MARK}{r.title} (captures blank)")
    if r.ok or not r.error.startswith(_BLOCKED_MARK):
        return r
    kw.pop("headed", None)
    r2 = _extract_once(url, out_dir, headed=True, **kw)
    if r2.ok and not (kw.get("shots", True) and _blank_share(r2.bands) >= 0.85):
        return r2
    if r2.ok:
        return SiteExtract(url, r2.title, False,
                           f"every capture of this page is a flat sheet — an overlay "
                           f"covered it for the whole visit, headed and headless, so "
                           f"there is nothing to design from")
    title = r2.error[len(_BLOCKED_MARK):] if r2.error.startswith(_BLOCKED_MARK) else ""
    return SiteExtract(url, r2.title, False,
                       f"blocked before the page loaded — served {title or r2.title!r} "
                       f"instead of the site (bot wall or network filter), so there "
                       f"is nothing to read")

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

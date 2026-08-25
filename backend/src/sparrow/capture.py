"""Browser capture for `inspector`.

SCROLL BEFORE YOU SHOOT. Entrance animations bound to `whileInView` start at
opacity 0 and never fire under a plain full-page screenshot, because a full-page
screenshot does not scroll. In experiments/drift-test-01 the first capture pass
reported three of five sections as blank. An inspector shipped without this
would spend the entire retry budget "fixing" sections that were already correct.
"""

from __future__ import annotations

import contextlib
import http.server
import socketserver
import threading
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

BREAKPOINTS: dict[str, tuple[int, int]] = {
    "desktop": (1440, 900),
    "tablet": (834, 1112),
    "mobile": (390, 844),
}

# Half a viewport at a time, with a dwell long enough for a 400ms entrance to
# start and an IntersectionObserver to fire.
_SCROLL = """
async () => {
  const step = window.innerHeight / 2;
  for (let y = 0; y < document.body.scrollHeight; y += step) {
    window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 120));
  }
  window.scrollTo(0, 0);
  await new Promise(r => setTimeout(r, 300));
}
"""


@dataclass
class Shot:
    breakpoint: str
    path: Path
    hidden_elements: list[str]


@dataclass
class SectionShot:
    """One section, at one breakpoint.

    Per-section rather than full-page, for a reason that is arithmetic rather
    than taste. Image tokens are (w*h)/750 after a resize to 1568px on the long
    edge, so a 1440x8690 full-page capture is squashed to roughly 260px wide —
    543 tokens of unreadable postage stamp. A single 1440x900 section is 1,728
    tokens and legible. Per-section also lets a defect name the section it is in.
    """

    section_index: int
    breakpoint: str
    path: Path
    width: int
    height: int

    @property
    def image_tokens(self) -> int:
        scale = min(1.0, 1568 / max(self.width, self.height))
        return int((self.width * scale) * (self.height * scale) / 750)

    def b64(self) -> str:
        import base64
        return base64.b64encode(self.path.read_bytes()).decode()


@dataclass
class PageReport:
    """Everything deterministic, gathered before any model is asked anything."""

    console_errors: list[str]
    failed_requests: list[str]
    horizontal_overflow: list[str]
    fold_fade: list[str]
    spill: list[str]
    contrast_failures: list[str]
    sections: list[SectionShot]


@contextlib.contextmanager
def serve(directory: Path, port: int = 4321):
    """Serve a static export for the duration of a capture run."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(directory), **kw)

        def log_message(self, *a):  # silence
            pass

    with socketserver.TCPServer(("", port), Handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://localhost:{port}/"
        finally:
            httpd.shutdown()


def capture(
    url: str,
    out_dir: Path,
    *,
    breakpoints: list[str] | None = None,
    scale: int = 2,
) -> list[Shot]:
    out_dir.mkdir(parents=True, exist_ok=True)
    names = breakpoints or list(BREAKPOINTS)
    shots: list[Shot] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name in names:
            w, h = BREAKPOINTS[name]
            page = browser.new_page(
                viewport={"width": w, "height": h}, device_scale_factor=scale
            )
            page.goto(url, wait_until="domcontentloaded")
            # Sample BEFORE anything settles — this is what a visitor sees first.
            page.wait_for_timeout(150)
            fold_fade = page.evaluate(_FOLD_FADE)
            page.wait_for_load_state("networkidle")
            page.evaluate(_SCROLL)
            page.wait_for_timeout(600)

            hidden = page.evaluate(_INVISIBLE)

            path = out_dir / f"{name}-full.png"
            page.screenshot(path=str(path), full_page=True)
            shots.append(Shot(name, path, hidden))
            page.close()
        browser.close()
    return shots


_CONTRAST = r"""
() => {
  // Do NOT parse the computed colour string. Chrome returns whatever space the
  // author wrote in — Tailwind v4 tokens are oklch, which computes to
  // `lab(37.49 -32.00 16.52)`. Read as rgb() that is near-black, and every
  // ratio comes out around 1.4:1. Painting to a canvas makes the browser do the
  // conversion, and works for any colour syntax it can parse.
  const px = (() => {
    const c = document.createElement('canvas');
    c.width = c.height = 1;
    const ctx = c.getContext('2d', { willReadFrequently: true });
    return (colour, under) => {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = under || '#ffffff';
      ctx.fillRect(0, 0, 1, 1);
      ctx.fillStyle = colour;              // composited over `under`
      ctx.fillRect(0, 0, 1, 1);
      const d = ctx.getImageData(0, 0, 1, 1).data;
      return [d[0], d[1], d[2]];
    };
  })();

  const lum = ([r, g, b]) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };

  // Composite every ancestor background down to an opaque colour.
  const groundOf = (el) => {
    const stack = [];
    for (let n = el; n; n = n.parentElement) {
      const bg = getComputedStyle(n).backgroundColor;
      if (bg && bg !== 'transparent' && !/rgba\(0, 0, 0, 0\)/.test(bg)) stack.push(bg);
    }
    let rgb = [255, 255, 255];
    for (const bg of stack.reverse()) {
      rgb = px(bg, `rgb(${rgb.join(',')})`);
    }
    return rgb;
  };

  const out = [];
  for (const el of document.querySelectorAll('p,h1,h2,h3,h4,span,a,li,button,td')) {
    const t = (el.textContent || '').trim();
    if (!t || el.children.length) continue;
    const cs = getComputedStyle(el);
    if (parseFloat(cs.opacity) < 0.1 || cs.visibility === 'hidden') continue;
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight) || 400;
    const need = (size >= 24 || (size >= 18.66 && weight >= 700)) ? 3.0 : 4.5;
    try {
      const ground = groundOf(el);
      const fg = px(cs.color, `rgb(${ground.join(',')})`);
      const a = lum(fg), b = lum(ground);
      const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      if (ratio < need) {
        out.push(`${ratio.toFixed(2)}:1 (needs ${need}) — "${t.slice(0, 45)}"`);
      }
    } catch {}
  }
  return [...new Set(out)].slice(0, 15);
}
"""

# Document-level scrollWidth is NOT enough. Content can blow past the viewport
# and simply be clipped — by overflow:hidden on an ancestor, or by the viewport
# itself — leaving the page unscrollable but the content cut off. In
# drift-test-02 the mobile hero had both buttons and the entire product panel
# running off-screen while this check reported clean; only the vision pass saw
# it. So walk the box model instead, and report the OUTERMOST offender.
# Only opacity at or near ZERO is a defect. A threshold of 0.9 flagged seven
# elements that were deliberately dimmed to 0.80 and 0.96 alongside ten that were
# genuinely invisible — the noise buries the signal.
# Text above the fold that starts transparent and fades in leaves the first thing
# a visitor sees unreadable for the first few hundred milliseconds. Measured on a
# real build: 6 elements at exactly opacity 0 at first paint, settling only after
# ~1.2s. Every capture in this harness waits 2.5s, so it had never been seen.
#
# The sources do carry faint elements above the fold — 48 on kiro.dev — but their
# counts do not change between 150ms and 2s: that is deliberate dimming, not a
# reveal. The defect is text that is transparent AT FIRST PAINT.
_FOLD_FADE = r"""
() => [...document.querySelectorAll('main *')]
  .filter(e => {
    const r = e.getBoundingClientRect();
    if (r.top > innerHeight || r.height < 8) return false;
    if (!(e.textContent || '').trim() || e.children.length) return false;
    return parseFloat(getComputedStyle(e).opacity) < 0.5;
  })
  .map(e => {
    const t = (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 44);
    return `opacity ${getComputedStyle(e).opacity} at first paint — "${t}"`;
  })
  .slice(0, 8)
"""

# Content wider than the box that holds it. Distinct from viewport overflow,
# which only catches things pushing past the page edge: a 45px grid cell holding
# 116px of text spills over its neighbour without the document ever scrolling.
# Observed on a real build — "change/retry-policy" and "docs/specs/**" painting
# outside their cells — and invisible to every check in the harness, which is why
# three rounds of fixing never touched it.
#
# scrollWidth vs clientWidth catches it whether the parent clips or not: if it
# clips, the text is silently truncated; if it does not, the text spills.
_SPILL = r"""
() => [...document.querySelectorAll('main *')]
  .filter(e => {
    if (e.children.length) return false;
    const t = (e.textContent || '').trim();
    if (!t) return false;
    const r = e.getBoundingClientRect();
    if (r.width < 8 || r.height < 6) return false;
    return e.scrollWidth - e.clientWidth > 8;
  })
  .map(e => {
    const t = (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    const over = e.scrollWidth - e.clientWidth;
    const clipped = /hidden|clip/.test(getComputedStyle(e.parentElement).overflow);
    return `"${t}" needs ${e.scrollWidth}px in a ${e.clientWidth}px box `
         + `(${over}px ${clipped ? 'truncated' : 'spilling outside it'})`;
  })
  .slice(0, 10)
"""

_UNSTICK = r"""
() => {
  for (const el of document.querySelectorAll('body *')) {
    const p = getComputedStyle(el).position;
    if (p === 'sticky' || p === 'fixed') {
      el.style.setProperty('position', 'static', 'important');
      el.style.setProperty('top', 'auto', 'important');
    }
  }
}
"""

_INVISIBLE = r"""
() => [...document.querySelectorAll('section, section *')]
  .filter(e => parseFloat(getComputedStyle(e).opacity) <= 0.05)
  .map(e => {
    const r = e.getBoundingClientRect();
    const t = (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    return `<${e.tagName.toLowerCase()}> y=${Math.round(r.top + scrollY)} "${t}"`;
  })
  .slice(0, 20)
"""

_OVERFLOW = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const bad = new Set();
  for (const el of document.querySelectorAll('main, main *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (r.right > vw + 1 || r.left < -1) bad.add(el);
  }
  const out = [];
  for (const el of bad) {
    // Only the outermost element of an overflowing subtree is the real defect.
    let p = el.parentElement, nested = false;
    while (p) { if (bad.has(p)) { nested = true; break; } p = p.parentElement; }
    if (nested) continue;
    const r = el.getBoundingClientRect();
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    out.push(
      `<${el.tagName.toLowerCase()}> spans ${Math.round(r.left)}px..${Math.round(r.right)}px ` +
      `in a ${vw}px viewport` + (t ? ` — "${t}"` : '')
    );
  }
  return out.slice(0, 8);
}
"""


def inspect_page(
    url: str,
    out_dir: Path,
    *,
    breakpoints: list[str] | None = None,
    scale: int = 2,
) -> dict[str, PageReport]:
    """Deterministic pass. No model is involved anywhere in this function.

    Everything a regex, a DOM query or arithmetic can answer is answered here,
    because a violation a computer can find is not worth a vision call.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, PageReport] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name in breakpoints or ["desktop", "mobile"]:
            w, h = BREAKPOINTS[name]
            page = browser.new_page(
                viewport={"width": w, "height": h}, device_scale_factor=scale
            )
            errors: list[str] = []
            failed: list[str] = []
            page.on("console", lambda m: errors.append(m.text[:200])
                    if m.type == "error" else None)
            page.on("requestfailed",
                    lambda r: failed.append(f"{r.method} {r.url[:110]}"))

            page.goto(url, wait_until="domcontentloaded")
            # Sample BEFORE anything settles — this is what a visitor sees first.
            page.wait_for_timeout(150)
            fold_fade = page.evaluate(_FOLD_FADE)
            page.wait_for_load_state("networkidle")
            page.evaluate(_SCROLL)
            page.wait_for_timeout(600)

            # Playwright scrolls an element to the top of the viewport before
            # capturing it, so a sticky header lands on top of whatever is being
            # captured. Every section then looks like it has a nav bar over its
            # first line. Neutralise sticky/fixed for the duration so the
            # inspector sees the section, not the chrome.
            page.add_style_tag(content=(
                "[data-sparrow-unstick]{position:static!important;top:auto!important}"
            ))
            page.evaluate("""() => {
              for (const el of document.querySelectorAll('body *')) {
                const p = getComputedStyle(el).position;
                if (p === 'sticky' || p === 'fixed') el.setAttribute('data-sparrow-unstick', '');
              }
            }""")

            shots: list[SectionShot] = []
            for i, el in enumerate(page.query_selector_all("main > section, main > div > section")):
                box = el.bounding_box()
                if not box or box["height"] < 40:
                    continue
                path = out_dir / f"{name}-s{i:02d}.png"
                el.screenshot(path=str(path))
                shots.append(SectionShot(
                    i, name, path, int(box["width"]), int(box["height"])
                ))

            reports[name] = PageReport(
                console_errors=sorted(set(errors))[:10],
                failed_requests=sorted(set(failed))[:10],
                horizontal_overflow=page.evaluate(_OVERFLOW),
                fold_fade=fold_fade,
                spill=page.evaluate(_SPILL),
                contrast_failures=page.evaluate(_CONTRAST),
                sections=shots,
            )
            page.close()
        browser.close()
    return reports

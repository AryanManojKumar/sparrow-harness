"""Screenshots of the built export, for the agent to look at what it made.

A build that passes says nothing about the page: the spike's pricing page
compiled cleanly with its check marks invisible on a dark card. The builder
loop in the pipeline already looks after it builds (§6); this is the same step
for the studio, sized for it — the pages a turn touched, not the whole site.

The export is served to the browser from disk through request interception, on
a host that does not exist. Nothing listens on a port and every request that is
not for the export is aborted, so model-written JavaScript in the page cannot
reach the network from here either.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image

HOST = "http://studio.invalid"
WIDTH = 1440
TILE = 1800        # css px of page per image, at least
MAX_TILES = 4      # per route; a 10,000px home page gets 4 taller tiles, not 6
SCALE_TO = 900     # px wide after downscaling, enough to read layout and contrast

_PAGE = re.compile(r"^src/app/(?:(.+)/)?page\.(?:tsx|jsx|ts|js|mdx)$")
_BASE = re.compile(r"basePath:\s*[\"']([^\"']+)[\"']")


def base_path(workspace: Path) -> str:
    cfg = workspace / "next.config.ts"
    m = _BASE.search(cfg.read_text()) if cfg.is_file() else None
    return m.group(1).rstrip("/") if m else ""


def routes_for(changed: list[str], limit: int = 2) -> list[str]:
    """The pages worth looking at after these files changed.

    A changed page file is that page. Anything else — a section, a component,
    the styles — shows up on the home page first.
    """
    routes: list[str] = []
    for path in changed:
        m = _PAGE.match(path)
        if m:
            seg = m.group(1) or ""
            # Route groups like (marketing) are not part of the URL.
            seg = "/".join(p for p in seg.split("/") if not p.startswith("("))
            routes.append(f"/{seg}/" if seg else "/")
    if not routes or any(not _PAGE.match(p) for p in changed):
        routes.insert(0, "/")
    out: list[str] = []
    for r in routes:
        if r not in out and "[" not in r:  # dynamic routes have no single page
            out.append(r)
    return (out or ["/"])[:limit]


def _jpeg(png: bytes) -> str:
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.width > SCALE_TO:
        im = im.resize((SCALE_TO, round(im.height * SCALE_TO / im.width)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def _server(export: Path, base: str):
    """The request handler that serves the export from disk and nothing else."""
    root = export.resolve()

    def serve(route) -> None:
        url = route.request.url
        if not url.startswith(HOST + base + "/") and url != HOST + base:
            return route.abort()
        rel = url[len(HOST + base):].split("?", 1)[0].split("#", 1)[0].lstrip("/")
        target = (root / rel).resolve()
        if not target.is_relative_to(root):
            return route.abort()
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file() and target.with_suffix(".html").is_file():
            target = target.with_suffix(".html")
        if not target.is_file():
            return route.fulfill(status=404, body="not found")
        return route.fulfill(path=str(target))

    return serve


def _walk(page) -> None:
    """Scroll the page through once so whileInView entrances settle."""
    height = page.evaluate("document.documentElement.scrollHeight")
    for y in range(0, height, 900):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(80)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)


# Per image: how much of the FILE the reader sees. object-fit: cover crops to
# the box's shape, and every ancestor that clips (overflow other than visible)
# cuts the box down further. Per heading: its rendered size.
_MEASURE = """() => {
  const images = [...document.images].map(i => {
    const r = i.getBoundingClientRect();
    let v = {l: r.left, t: r.top, r: r.right, b: r.bottom};
    for (let e = i.parentElement; e && e !== document.body; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') {
        const p = e.getBoundingClientRect();
        v = {l: Math.max(v.l, p.left), t: Math.max(v.t, p.top),
             r: Math.min(v.r, p.right), b: Math.min(v.b, p.bottom)};
      }
    }
    const area = r.width * r.height;
    const clipped = area ? Math.max(0, v.r - v.l) * Math.max(0, v.b - v.t) / area : 0;
    const rn = i.naturalWidth / (i.naturalHeight || 1), rd = r.width / (r.height || 1);
    const fit = getComputedStyle(i).objectFit === 'cover' ? Math.min(rn, rd) / Math.max(rn, rd) : 1;
    return {src: i.currentSrc || i.src, natural: [i.naturalWidth, i.naturalHeight],
            box: [Math.round(r.width), Math.round(r.height)],
            visible: Math.round(clipped * fit * 100) / 100};
  }).filter(x => x.box[0] > 40 && x.box[1] > 40);
  const headings = [...document.querySelectorAll('h1, h2')].map(h => ({
    tag: h.tagName.toLowerCase(), size: parseFloat(getComputedStyle(h).fontSize),
    text: h.innerText.slice(0, 80)}));
  return {images, headings};
}"""


def measure(export: Path, base: str, route: str = "/") -> dict:
    """{images: [{src, natural, box, visible}], headings: [{tag, size, text}]}."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": WIDTH, "height": 900},
                                    reduced_motion="reduce")
            page.route("**/*", _server(export, base))
            page.goto(HOST + base + route, wait_until="load")
            _walk(page)
            return page.evaluate(_MEASURE)
        finally:
            browser.close()


def shoot(export: Path, base: str, routes: list[str]) -> list[dict]:
    """[{route, part, of, data}] — base64 JPEGs, top to bottom per route."""
    from playwright.sync_api import sync_playwright

    serve = _server(export, base)
    shots: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": WIDTH, "height": 900},
                                    reduced_motion="reduce")
            page.route("**/*", serve)
            for r in routes:
                page.goto(HOST + base + r, wait_until="load")
                _walk(page)
                height = page.evaluate("document.documentElement.scrollHeight")
                # Taller tiles on a long page, so four always reach the footer.
                tile = max(TILE, -(-height // MAX_TILES))
                tiles = max(1, -(-height // tile))
                for i in range(tiles):
                    png = page.screenshot(full_page=True, clip={
                        "x": 0, "y": i * tile, "width": WIDTH,
                        "height": min(tile, height - i * tile)})
                    shots.append({"route": r, "part": i + 1, "of": tiles, "data": _jpeg(png)})
        finally:
            browser.close()
    return shots

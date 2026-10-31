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


def shoot(export: Path, base: str, routes: list[str]) -> list[dict]:
    """[{route, part, of, data}] — base64 JPEGs, top to bottom per route."""
    from playwright.sync_api import sync_playwright

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

    shots: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": WIDTH, "height": 900},
                                    reduced_motion="reduce")
            page.route("**/*", serve)
            for r in routes:
                page.goto(HOST + base + r, wait_until="load")
                # Let whileInView entrances settle as the page is walked.
                height = page.evaluate("document.documentElement.scrollHeight")
                for y in range(0, height, 900):
                    page.evaluate(f"window.scrollTo(0, {y})")
                    page.wait_for_timeout(80)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(400)
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

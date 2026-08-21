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
            page.goto(url, wait_until="networkidle")
            page.evaluate(_SCROLL)
            page.wait_for_timeout(600)

            hidden = page.evaluate("""
              () => [...document.querySelectorAll('section, section *')]
                .filter(e => parseFloat(getComputedStyle(e).opacity) < 0.9)
                .map(e => e.tagName + '.' + (e.className || '').toString().slice(0, 40))
                .slice(0, 20)
            """)

            path = out_dir / f"{name}-full.png"
            page.screenshot(path=str(path), full_page=True)
            shots.append(Shot(name, path, hidden))
            page.close()
        browser.close()
    return shots

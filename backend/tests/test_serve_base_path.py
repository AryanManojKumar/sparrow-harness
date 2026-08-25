"""serve() must serve an export at the path that export was built for.

Previews are built with Next's basePath (commit 209cdc7) so they work under
/projects/{id}/preview. capture.serve() served the directory at "/", so every
prefixed asset URL 404'd and the whole verify loop inspected an unstyled page.

Both cases are covered on purpose: a prefixed export must be reachable, and a
root export must keep working. A fix that only satisfies the first would break
every project built before basePath landed.
"""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from sparrow.capture import base_path, serve

PROJECTS = Path(__file__).resolve().parents[2] / "projects"
PREFIXED = PROJECTS / "i-want-to-make-a-website-for-my-ide-that-iecrg/workspace/out"
ROOT = PROJECTS / "drift-test/workspace/out"


def _render(directory: Path, port: int):
    """Load the export through serve() and report what the browser got."""
    with serve(directory, port=port) as url, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        failed: list[str] = []
        page.on("response", lambda r: r.status >= 400 and failed.append(r.url))
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(400)
        font = page.evaluate(
            "getComputedStyle(document.querySelector('h1') || document.body).fontFamily"
        )
        browser.close()
        return url, failed, font


@pytest.mark.skipif(not PREFIXED.is_dir(), reason="no prefixed export built")
def test_prefixed_export_is_served_at_its_base_path():
    mount = base_path(PREFIXED)
    assert mount == "/projects/i-want-to-make-a-website-for-my-ide-that-iecrg/preview"

    url, failed, font = _render(PREFIXED, 4341)
    assert url.endswith(mount + "/"), url
    assert not failed, f"{len(failed)} asset(s) 404'd: {failed[:3]}"
    # Times New Roman is the tell: no stylesheet reached the page.
    assert "Times" not in font, font


@pytest.mark.skipif(not ROOT.is_dir(), reason="no root export built")
def test_root_export_still_works():
    assert base_path(ROOT) == ""

    url, failed, font = _render(ROOT, 4342)
    assert url == "http://localhost:4342/", url
    assert not failed, f"{len(failed)} asset(s) 404'd: {failed[:3]}"
    assert "Times" not in font, font

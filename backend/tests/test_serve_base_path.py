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

BASE = "/projects/p1/preview"


def _export(root: Path, mount: str) -> Path:
    """A minimal Next-shaped static export, built here rather than borrowed.

    This used to point at two real projects under projects/. One of them was
    later rebuilt without basePath and the test started failing on stale
    fixture data rather than on a regression — a test that depends on live
    project state tells you about the state, not the code.
    """
    out = root / ("prefixed" if mount else "root")
    (out / "_next/static/chunks").mkdir(parents=True, exist_ok=True)
    (out / "_next/static/chunks/app.css").write_text(
        "body{font-family:Archivo,sans-serif;background:#0b1f14}")
    (out / "index.html").write_text(
        f'<html><head><link rel="stylesheet" '
        f'href="{mount}/_next/static/chunks/app.css"></head>'
        f"<body><h1>hello</h1></body></html>")
    return out


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


def test_prefixed_export_is_served_at_its_base_path(tmp_path):
    directory = _export(tmp_path, BASE)
    mount = base_path(directory)
    assert mount == BASE

    url, failed, font = _render(directory, 4341)
    assert url.endswith(mount + "/"), url
    assert not failed, f"{len(failed)} asset(s) 404'd: {failed[:3]}"
    # Times New Roman is the tell: no stylesheet reached the page.
    assert "Times" not in font, font


def test_root_export_still_works(tmp_path):
    directory = _export(tmp_path, "")
    assert base_path(directory) == ""

    url, failed, font = _render(directory, 4342)
    assert url == "http://localhost:4342/", url
    assert not failed, f"{len(failed)} asset(s) 404'd: {failed[:3]}"
    assert "Times" not in font, font

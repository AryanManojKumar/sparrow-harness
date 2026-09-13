"""A preview that is present is not necessarily usable.

Two things must agree and they drift independently: `basePath` in next.config.ts,
which Next uses for its own `_next/…` URLs, and the prefix on every `/assets/…`
src in the section sources, because `next/image` with `unoptimized` does not
prepend basePath. A Cloudflare deploy rewrote both back to root-relative twice,
and each time the preview served a page whose stylesheets loaded and whose every
image 404'd — which looks like a broken build rather than a mismatched one.
"""
from __future__ import annotations

import pytest

from conftest import make_run
from sparrow.steps import preview_base, preview_bound, rebind_preview

BASE = "/projects/p1/preview"


def _export(run, prefix: str) -> None:
    out = run.workspace / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        f'<link href="{prefix}/_next/static/chunks/a.css">')


@pytest.fixture
def run(tmp_path):
    return make_run(tmp_path, {"hero": "x"}, pid="p1")


def test_an_export_built_for_the_preview_path_is_bound(run):
    _export(run, BASE)
    assert preview_bound(run) is True


def test_a_root_relative_export_is_not_bound(run):
    _export(run, "")
    assert preview_bound(run) is False


def test_a_project_with_no_export_is_not_reported_as_broken(run):
    # Nothing built yet is not "unbound" — flagging it would put a repair
    # button on every project that has simply not run.
    assert preview_bound(run) is True


def test_rebinding_puts_the_prefix_back_on_every_asset_src(run):
    secs = run.workspace / "src/components/sections"
    (secs / "Hero.tsx").write_text('<Image src="/assets/hero-1.png" />')
    (secs / "Cta.tsx").write_text("<p>no imagery here</p>")

    changed = rebind_preview(run)
    assert changed["sections"] == ["Hero.tsx"]
    assert f'src="{BASE}/assets/hero-1.png"' in (secs / "Hero.tsx").read_text()
    # A section with no asset must not be rewritten, or every build churns.
    assert (secs / "Cta.tsx").read_text() == "<p>no imagery here</p>"


def test_rebinding_restores_basepath_in_the_config(run):
    cfg = run.workspace / "next.config.ts"
    cfg.write_text("const nextConfig = {\n  trailingSlash: true,\n};\n")

    assert rebind_preview(run)["config"] is True
    assert f'basePath: "{BASE}"' in cfg.read_text()
    assert f'assetPrefix: "{BASE}"' in cfg.read_text()


def test_rebinding_twice_changes_nothing_the_second_time(run):
    cfg = run.workspace / "next.config.ts"
    cfg.write_text("const nextConfig = {\n  trailingSlash: true,\n};\n")
    (run.workspace / "src/components/sections/Hero.tsx").write_text(
        '<Image src="/assets/hero-1.png" />')

    rebind_preview(run)
    second = rebind_preview(run)
    # Idempotent, so a UI can offer the button without fear of double-prefixing.
    assert second == {"config": False, "sections": []}


def test_preview_base_is_the_path_the_api_serves_from(run):
    assert preview_base(run) == BASE


def test_a_bound_config_with_root_relative_images_is_not_bound(run):
    """The false negative the first version of this check shipped with.

    `base_path` reads the `_next/` prefix, which comes from next.config.ts. Next
    prefixes its own chunks and leaves an unoptimized <Image> src exactly as
    written, so a project can have a correct config and 404 every image. The ide
    project was in exactly that state and this check called it healthy.
    """
    out = run.workspace / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        f'<link href="{BASE}/_next/static/chunks/a.css">'
        f'<img src="/assets/hero-1.png">')
    assert preview_bound(run) is False


def test_an_export_prefixed_in_both_halves_is_bound(run):
    out = run.workspace / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        f'<link href="{BASE}/_next/static/chunks/a.css">'
        f'<img src="{BASE}/assets/hero-1.png">')
    assert preview_bound(run) is True

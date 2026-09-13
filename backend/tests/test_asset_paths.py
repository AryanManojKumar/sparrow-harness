"""An image src must survive into the preview's base path.

A real run produced seven images and seven blank spaces: every src came back as
`/assets/…` and 404'd, because a preview is exported with Next's `basePath` and
`next/image` with `unoptimized` does not prepend it. `asset_base` was declared on
`Builder.build`, passed in from steps.py, and never read — the listing hard-coded
a leading "/".

The prompt now says so, but a prompt is not a guarantee: this is tested against
the deterministic pass, which is.
"""
from __future__ import annotations

import pytest

from sparrow.agents.builder import prefix_assets

BASE = "/projects/p1/preview"


def test_a_root_relative_src_gets_the_base():
    out = prefix_assets('<Image src="/assets/hero-1.png" alt="" />', BASE)
    assert out == '<Image src="/projects/p1/preview/assets/hero-1.png" alt="" />'


@pytest.mark.parametrize("quote", ['"', "'", "`"])
def test_every_quoting_style_next_accepts(quote):
    code = f"src={quote}/assets/a.png{quote}"
    assert f"{BASE}/assets/a.png" in prefix_assets(code, BASE)


def test_it_is_idempotent_so_a_fix_round_cannot_double_prefix():
    once = prefix_assets('src="/assets/a.png"', BASE)
    assert prefix_assets(once, BASE) == once


def test_a_path_that_already_carries_the_base_is_left_alone():
    code = f'src="{BASE}/assets/a.png"'
    assert prefix_assets(code, BASE) == code


def test_an_unrelated_absolute_path_is_not_touched():
    # Only /assets/ is ours. Rewriting every absolute path would break links.
    code = 'href="/pricing" src="/logo.svg"'
    assert prefix_assets(code, BASE) == code


def test_no_base_means_no_rewrite():
    code = 'src="/assets/a.png"'
    assert prefix_assets(code, "") == code


def test_a_trailing_slash_on_the_base_does_not_double_up():
    assert prefix_assets('src="/assets/a.png"', BASE + "/") == \
        f'src="{BASE}/assets/a.png"'


def test_write_section_applies_it(tmp_path):
    from sparrow.agents.builder import write_section
    from sparrow.blackboard.schema import Section

    s = Section(id="hero", order=1, blueprint_id="hero",
                target_path="src/components/sections/Hero.tsx",
                component_name="Hero")
    p = write_section(tmp_path, s, 'export default () => <img src="/assets/a.png" />',
                      asset_base=BASE)
    assert f"{BASE}/assets/a.png" in p.read_text()

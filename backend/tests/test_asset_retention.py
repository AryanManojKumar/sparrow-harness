"""A repair may not throw away the user's imagery.

Measured on the voice-ai run: the fixer repaired three defects in
integration-grid and one in feature-grid, and removed the <Image> for
integration-grid-1 and feature-grid-1 in the process. Both were the user's OWN
uploaded files — still on disk, still on the blackboard, referenced by nothing.
The sections rendered without them and no check noticed, so the repair loop
quietly deleted the one thing CLAUDE.md §2 calls the differentiator.
"""
from __future__ import annotations

import pytest

from sparrow.steps import _assets_lost

WITH = '<Image src="/assets/feature-grid-1.png" alt="" /><p>copy</p>'
WITHOUT = "<p>copy</p>"


def test_a_removed_image_is_reported():
    assert _assets_lost(WITH, WITHOUT) == ["assets/feature-grid-1.png"]


def test_a_fix_that_keeps_the_image_is_clean():
    moved = '<div class="mt-8"><Image src="/assets/feature-grid-1.png" alt="x" /></div>'
    assert _assets_lost(WITH, moved) == []


def test_a_prefixed_path_is_still_recognised():
    # write_section rewrites srcs to the preview base path, so the two sides of
    # this comparison are not always spelled the same.
    prefixed = '<Image src="/projects/p1/preview/assets/feature-grid-1.png" />'
    assert _assets_lost(WITH, prefixed) == []


def test_adding_an_image_is_not_a_loss():
    more = WITH + '<Image src="/assets/feature-grid-2.png" />'
    assert _assets_lost(WITH, more) == []


def test_a_section_that_never_had_an_image_is_unaffected():
    # The common case. A guard that fired here would block every text-only fix.
    assert _assets_lost("<p>a</p>", "<p>b</p>") == []


def test_several_lost_images_are_all_named():
    both = WITH + '<Image src="/assets/integration-grid-1.png" />'
    assert _assets_lost(both, WITHOUT) == [
        "assets/feature-grid-1.png", "assets/integration-grid-1.png"]

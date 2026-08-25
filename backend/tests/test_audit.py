"""The drift audit, tested from both sides.

Every check here has a positive AND a negative case, because a deterministic
check that has only ever been shown firing is a check nobody has shown is right.
This file exists because of one that was not: `GAP = r"\\bgap-\\d+\\b"` matched
"gap-2" inside "gap-2.5" and reported it as off-scale. On the ide-01 run that
produced 31 findings — all 31 against `gap-2.5`, which is the literal string that
run's design system declared as `inline_gap`. The builder had obeyed the spec
exactly and the audit called it drift thirty-one times.

Nothing here costs anything: the audit is regex over text.
"""

from __future__ import annotations

import pytest

from sparrow.audit import audit_file, gap_size, permitted
from sparrow.fixtures.ledgerline import DESIGN_SYSTEM

# ledgerline declares grid_gap "gap-8", inline_gap "gap-3", weights 400/500/600,
# radius "rounded-lg"/"rounded-md", shadows "shadow-sm"/"shadow-md".
DS = DESIGN_SYSTEM


def categories(tmp_path, line: str, ds=DS) -> list[str]:
    f = tmp_path / "Section.tsx"
    f.write_text(f'export default function S() {{ return <div className="{line}" />; }}\n')
    return [x.category for x in audit_file(f, ds)]


# ------------------------------------------------------------------ the gap bug


@pytest.fixture
def fractional(monkeypatch):
    """A design system whose declared inline gap is fractional, as ide-01's was."""
    return DS.model_copy(update={"grid_gap": "gap-5 md:gap-8", "inline_gap": "gap-2.5"})


def test_a_declared_fractional_gap_is_not_drift(tmp_path, fractional):
    """The regression. This is the exact string ide-01 was flagged on 31 times."""
    assert categories(tmp_path, "flex gap-2.5", fractional) == []


def test_a_fractional_gap_is_not_silently_truncated_to_its_whole_part(tmp_path):
    """gap-2.5 must not be read as gap-2 — against a system that permits neither,
    the finding has to name what is actually in the file."""
    f = tmp_path / "Section.tsx"
    f.write_text('<div className="gap-2.5" />\n')
    found = audit_file(f, DS)
    assert [x.detail for x in found] == ["gap-2.5"], \
        "the finding must quote the real utility, not a prefix of it"


def test_an_undeclared_gap_is_still_caught(tmp_path):
    """The positive. Loosening the regex must not have made it blind."""
    assert categories(tmp_path, "flex gap-7") == ["off-scale-gap"]
    assert categories(tmp_path, "flex gap-2.5") == ["off-scale-gap"]


def test_a_declared_gap_passes(tmp_path):
    assert categories(tmp_path, "flex gap-8") == []
    assert categories(tmp_path, "flex gap-3") == []


def test_a_responsive_set_is_one_decision(tmp_path, fractional):
    """"gap-5 md:gap-8" is one declared value expressed as two utilities."""
    assert categories(tmp_path, "grid gap-5 md:gap-8", fractional) == []


def test_an_axis_variant_of_a_declared_gap_passes(tmp_path):
    """gap-x-8 is the declared gap-8 applied to one axis, not a new value."""
    assert categories(tmp_path, "flex gap-x-8") == []
    assert categories(tmp_path, "flex gap-y-3") == []


def test_an_axis_variant_of_an_undeclared_gap_is_caught(tmp_path):
    assert categories(tmp_path, "flex gap-x-7") == ["off-scale-gap"]


def test_gap_size_normalises_both_sides(tmp_path):
    assert gap_size("gap-2.5") == "2.5"
    assert gap_size("gap-x-8") == "8"
    assert gap_size("md:gap-5") == "5"


# ------------------------------------------- the other scales, both directions


@pytest.mark.parametrize("good,bad,category", [
    ("font-semibold", "font-bold", "off-scale-weight"),
    ("text-3xl", "text-2xl", "off-scale-type"),
    ("shadow-sm", "shadow-xl", "off-scale-shadow"),
    ("rounded-lg", "rounded-3xl", "off-scale-radius"),
])
def test_each_scale_fires_on_drift_and_stays_quiet_on_the_declared_value(
        tmp_path, good, bad, category):
    assert categories(tmp_path, bad) == [category], f"{bad} should be {category}"
    assert categories(tmp_path, good) == [], f"{good} is declared and must pass"


def test_rounded_full_is_always_allowed(tmp_path):
    """Declared separately by `radius_full_allowed` — avatars and pills are round
    regardless of what the card radius is."""
    assert categories(tmp_path, "rounded-full") == []


def test_a_literal_palette_colour_is_drift_but_a_token_is_not(tmp_path):
    assert categories(tmp_path, "text-slate-500") == ["literal-color"]
    assert categories(tmp_path, "bg-white") == ["literal-color"]
    assert categories(tmp_path, "text-foreground bg-background border-border") == []


def test_permitted_quotes_the_design_system_verbatim():
    """What the audit forbids and what the fixer is told to use are one derivation."""
    allow = permitted(DS)
    assert allow["off-scale-gap"] == {"gap-8", "gap-3"}
    assert allow["off-scale-weight"] == {"font-normal", "font-medium", "font-semibold"}
    assert "rounded-full" in allow["off-scale-radius"]

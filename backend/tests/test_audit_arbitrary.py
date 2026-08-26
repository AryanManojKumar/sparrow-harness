"""The audit must see arbitrary values, not just named Tailwind steps.

SHADOW and TEXT_STEP were closed alternations, so `shadow-[0_2px_0_0_oklch(...)]`
matched nothing and was silently permitted. Measured on the real projects:
ide-01 carried 11 shadows in a colour and offset its design system never
declared — a different oklch hue from `shadow_rest`, used eleven times. Invisible
to the audit because it was not one of Tailwind's named steps.

Both directions are tested. A widened pattern that flags a DECLARED arbitrary
value would be worse than the blind spot: three of the six real projects declare
their shadows as arbitrary values, so every card in them would be reported as
drift on every round, and the fixer would be paid to rewrite correct code.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sparrow.audit import audit_file, bare
from sparrow.fixtures.ledgerline import DESIGN_SYSTEM

ARB_SHADOW = "shadow-[0_2px_0_0_oklch(0.805_0.032_235)]"


def _audit(tmp_path: Path, source: str, ds=DESIGN_SYSTEM):
    f = tmp_path / "Section.tsx"
    f.write_text(source)
    return audit_file(f, ds)


def test_arbitrary_shadow_is_flagged_when_undeclared(tmp_path):
    # The fixture declares shadow-sm / shadow-md, so an arbitrary value is drift.
    found = _audit(tmp_path, f'<div className="rounded-md {ARB_SHADOW}" />')
    assert [f.category for f in found] == ["off-scale-shadow"]
    assert found[0].detail == ARB_SHADOW


def test_arbitrary_shadow_is_permitted_when_declared(tmp_path):
    ds = DESIGN_SYSTEM.model_copy(update={"shadow_rest": ARB_SHADOW})
    assert _audit(tmp_path, f'<div className="{ARB_SHADOW}" />', ds) == []


def test_named_shadow_still_works_both_ways(tmp_path):
    assert _audit(tmp_path, '<div className="shadow-sm" />') == []
    assert [f.category for f in _audit(tmp_path, '<div className="shadow-xl" />')] == [
        "off-scale-shadow"
    ]


def test_arbitrary_type_step_is_flagged_but_a_colour_is_not(tmp_path):
    found = _audit(tmp_path, '<h1 className="text-[clamp(3rem,7vw,6.5rem)]" />')
    assert [f.category for f in found] == ["off-scale-type"]

    # text-[#0f172a] is a colour. The type rule must not claim it — the colour
    # rules own it, and double-reporting one utility bills the fixer twice.
    assert "off-scale-type" not in {
        f.category for f in _audit(tmp_path, '<p className="text-[#0f172a]" />')
    }


def test_declared_arbitrary_type_step_is_permitted(tmp_path):
    step = DESIGN_SYSTEM.type_steps[0].model_copy(
        update={"classes": "text-[clamp(3rem,7vw,6.5rem)] tracking-tight"}
    )
    ds = DESIGN_SYSTEM.model_copy(update={"type_steps": [step, *DESIGN_SYSTEM.type_steps[1:]]})
    assert _audit(tmp_path, '<h1 className="text-[clamp(3rem,7vw,6.5rem)]" />', ds) == []


@pytest.mark.parametrize(
    "utility, expected",
    [
        ("shadow-sm", "shadow-sm"),
        ("md:shadow-sm", "shadow-sm"),
        ("hover:md:shadow-sm", "shadow-sm"),
        # The variant is stripped, the typed arbitrary value is left intact.
        ("md:shadow-[color:red]", "shadow-[color:red]"),
        ("shadow-[color:red]", "shadow-[color:red]"),
    ],
)
def test_bare_strips_variants_without_cutting_arbitrary_values(utility, expected):
    assert bare(utility) == expected

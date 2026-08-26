"""The counted component vocabulary must reach the blueprinter's prompt.

The scout measures what a category builds pages out of — tabs, accordions, pill
rows, code blocks, stat numbers, inline SVG — and the system prompt already told
the model to use the sources' vocabulary. But `Components.used()` had no caller
anywhere in the repo: the counts were measured, stored on the extract, and never
rendered. The model was told to match a vocabulary it was never shown, which is
why blueprints defaulted to icon-title-body cards.
"""
from __future__ import annotations

from sparrow.agents.blueprinter import Blueprinter
from sparrow.blackboard.schema import Brief
from sparrow.scout import Components

BRIEF = Brief(category="Developer tool", offering="An IDE.", audience="Engineers.",
              tone="Restrained.", primary_action="Download")


class _Reply:
    text = '{"id": "x", "purpose": "p", "slots": ["a"], "assets": [], "structure": "s"}'
    usage = None


def _prompt(monkeypatch, vocabulary):
    seen = {}

    def fake_call(self, *, system, user, images=None):
        seen["user"], seen["system"] = user, system
        return _Reply()

    monkeypatch.setattr(Blueprinter, "call", fake_call)
    b = Blueprinter(type("P", (), {"_agent_name": ""})())
    b.write(BRIEF, "feature-grid", {"winner": "kiro.dev", "why": "w", "adopt": []},
            [], [], vocabulary=vocabulary)
    return seen["user"]


def test_counted_components_reach_the_prompt(monkeypatch):
    user = _prompt(monkeypatch, {
        "kiro.dev": Components(accordions=17, inline_svg=62, tabs=3),
    })
    assert "counted_vocabulary" in user
    assert "accordions (17)" in user
    assert "inline SVG / diagrams (62)" in user


def test_a_component_the_sources_barely_use_is_not_offered(monkeypatch):
    # `used()` reports at a threshold of 2. One stray <table> on one page is not
    # a category convention, and offering it invites a component for variety's
    # sake — which the system prompt explicitly forbids.
    user = _prompt(monkeypatch, {"kiro.dev": Components(tables=1, accordions=9)})
    assert "tables" not in user
    assert "accordions (9)" in user


def test_no_vocabulary_means_no_empty_block(monkeypatch):
    # An empty <counted_vocabulary> block is worse than none: it reads as
    # "the sources use nothing", which is a measurement nobody made.
    assert "counted_vocabulary" not in _prompt(monkeypatch, {})
    assert "counted_vocabulary" not in _prompt(monkeypatch, None)


def test_a_source_with_nothing_counted_is_omitted_but_others_survive(monkeypatch):
    user = _prompt(monkeypatch, {"empty.com": Components(),
                                 "linear.app": Components(pills=8, code_blocks=11)})
    assert "empty.com" not in user
    assert "pills (8)" in user and "code blocks (11)" in user

"""End to end across the new stage order: content → material gate → build.

No model calls, no browser, no money. What is under test is the seam, not the
copy: that a drafted slot survives the gate, that a user's answer replaces the
draft and is marked as theirs, and that what the builder is finally handed is
the answered copy rather than a fresh invention. Every one of those is a place
where a value can be computed and then quietly dropped, which is the failure
this repo keeps finding.
"""

from __future__ import annotations

import json

import pytest

from conftest import make_run
from sparrow.agents.content_editor import Ask, Copy, Source
from sparrow.blackboard.schema import Blueprint
from sparrow.orchestrator import Halt, Stage
from sparrow.steps import (
    content_asks,
    load_content,
    record_content_answers,
    step_asset_gate,
    step_content,
)

BLUEPRINTS = {
    "hero": Blueprint(
        id="hero", purpose="Introduce the product.",
        slots=["headline", "body"], assets=[], structure="stacked",
    ),
    "nav": Blueprint(
        id="nav", purpose="Navigate.",
        slots=["brand_label"], assets=[], structure="bar",
    ),
}


class StubEditor:
    """Drafts fixed copy, and invents one fact in the hero and none in the nav.

    That asymmetry is the point of the agent: a nav has nothing to make up, a
    hero usually does. A stub that raised an ask everywhere would let a gate
    that ignores `asks` pass.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def write(self, _brief, _constraints, blueprint, *, section_id, source_slots=None):
        self.calls.append(section_id)
        if section_id == "nav":
            return Copy(section_id="nav",
                        slots={"brand_label": "Ledgerline"},
                        provenance={"brand_label": Source.DRAFTED})
        return Copy(
            section_id="hero",
            slots={"headline": "Trusted by 400 teams", "body": "Reconcile faster."},
            provenance={"headline": Source.DRAFTED, "body": Source.DRAFTED},
            asks=[Ask(id="hero-1", section_id="hero", slot="headline",
                      question="How many teams use it today?",
                      draft="Trusted by 400 teams",
                      invented="400 teams")],
        )


@pytest.fixture
def run(tmp_path, monkeypatch):
    r = make_run(tmp_path, {"nav": "x", "hero": "y"})
    import sparrow.blueprints as blueprints_mod
    monkeypatch.setattr(blueprints_mod, "load_dir", lambda _d: BLUEPRINTS)
    return r


@pytest.fixture
def editor(monkeypatch):
    stub = StubEditor()
    import sparrow.agents.content_editor as mod
    monkeypatch.setattr(mod, "ContentEditor", lambda: stub)
    return stub


def _drain(it):
    return list(it)


# ------------------------------------------------------------- the content stage

def test_every_section_with_slots_is_drafted_and_written_to_disk(run, editor):
    events = _drain(step_content(run))

    assert sorted(editor.calls) == ["hero", "nav"]
    content = load_content(run)
    assert content["hero"]["slots"]["headline"] == "Trusted by 400 teams"
    assert content["nav"]["slots"]["brand_label"] == "Ledgerline"
    assert events[-1].kind == "done"
    assert "1 invented fact" in events[-1].message


def test_only_the_section_that_invented_something_raises_an_ask(run, editor):
    _drain(step_content(run))
    asks = content_asks(run)
    assert [a["section_id"] for a in asks] == ["hero"]
    assert asks[0]["invented"] == "400 teams"


def test_a_resumed_run_does_not_redraft_answered_copy(run, editor):
    _drain(step_content(run))
    record_content_answers(run, {"hero-1": "Trusted by 12 teams"})
    editor.calls.clear()

    _drain(step_content(run))
    # Redrafting here would silently throw away the fact the user just typed.
    assert editor.calls == []
    assert load_content(run)["hero"]["slots"]["headline"] == "Trusted by 12 teams"


# ---------------------------------------------------------------- the gate

def test_the_gate_carries_the_invented_facts_alongside_the_images(run, editor):
    _drain(step_content(run))
    with pytest.raises(Halt) as h:
        _drain(step_asset_gate(run))

    req = h.value.request
    assert req.gate is Stage.GATE_ASSETS
    facts = [o for o in req.options if o["kind"] == "fact"]
    assert len(facts) == 1
    assert facts[0]["draft"] == "Trusted by 400 teams"
    assert facts[0]["question"] == "How many teams use it today?"
    # §8: concrete options, not a dump of criteria.
    assert {c["choice"] for c in facts[0]["choices"]} == {"answer", "keep"}


def test_the_gate_still_opens_when_no_section_wants_an_image(run, editor):
    # Every blueprint here declares `assets=[]`. Before the content stage that
    # was "nothing to ask" and the gate closed itself; now the copy still has a
    # question, and closing would drop it.
    _drain(step_content(run))
    with pytest.raises(Halt):
        _drain(step_asset_gate(run))


def test_no_invented_fact_leaves_the_gate_with_no_fact_question(run, editor,
                                                                monkeypatch):
    """The gate still opens — this project has a nav, so it has a logo to ask
    about — but nothing in the copy is up for confirmation.

    It used to CLOSE here. It cannot any more: a nav means the site has a brand
    entry point, and whose mark goes in it is a question only the user can
    answer. Asserting "closes" would now pass only by the logo question having
    been dropped, which is the bug this asks about.
    """
    monkeypatch.setattr(
        StubEditor, "write",
        lambda self, _b, _c, bp, *, section_id, source_slots=None: Copy(
            section_id=section_id, slots={s: "x" for s in bp.slots},
            provenance={s: Source.DRAFTED for s in bp.slots}),
    )
    _drain(step_content(run))
    with pytest.raises(Halt) as h:
        _drain(step_asset_gate(run))

    kinds = [o["kind"] for o in h.value.request.options]
    assert kinds == ["logo"], "no invented fact, no content imagery — only the mark"


def test_a_project_with_no_nav_and_nothing_invented_does_not_stop(
        run, editor, monkeypatch, tmp_path):
    """The negative: with no brand entry point and no invented fact there is
    genuinely nothing to ask, and the run must not stop to say so."""
    import sparrow.blueprints as blueprints_mod

    solo = make_run(tmp_path, {"hero": "y"}, pid="nonav")
    monkeypatch.setattr(blueprints_mod, "load_dir",
                        lambda _d: {"hero": BLUEPRINTS["hero"]})
    monkeypatch.setattr(
        StubEditor, "write",
        lambda self, _b, _c, bp, *, section_id, source_slots=None: Copy(
            section_id=section_id, slots={s: "x" for s in bp.slots},
            provenance={s: Source.DRAFTED for s in bp.slots}),
    )
    _drain(step_content(solo))
    events = _drain(step_asset_gate(solo))
    assert events[-1].kind == "done"


# ------------------------------------------------------------ answering

def test_an_answer_replaces_the_draft_and_is_marked_as_the_users(run, editor):
    _drain(step_content(run))
    assert record_content_answers(run, {"hero-1": "Trusted by 12 teams"}) == 1

    hero = load_content(run)["hero"]
    assert hero["slots"]["headline"] == "Trusted by 12 teams"
    assert hero["provenance"]["headline"] == "user_supplied"
    assert hero["asks"] == []


def test_an_empty_answer_keeps_the_draft_and_still_closes_the_ask(run, editor):
    _drain(step_content(run))
    assert record_content_answers(run, {"hero-1": "   "}) == 0

    hero = load_content(run)["hero"]
    assert hero["slots"]["headline"] == "Trusted by 400 teams"
    assert hero["provenance"]["headline"] == "drafted"
    assert content_asks(run) == []


def test_an_unknown_ask_id_is_refused_rather_than_ignored(run, editor):
    _drain(step_content(run))
    # A dropped answer is worse than a refused one: the user typed a real fact
    # about their business and would never learn it went nowhere.
    with pytest.raises(ValueError, match="no such content ask"):
        record_content_answers(run, {"hero-9": "something true"})
    assert load_content(run)["hero"]["slots"]["headline"] == "Trusted by 400 teams"


# ------------------------------------------------------- what the builder gets

class CopyRecordingBuilder:
    provider = type("P", (), {"name": "fake"})()
    tier = "fake"

    def __init__(self) -> None:
        self.copies: dict[str, dict] = {}

    def build(self, _bb, section, _bp, **kw):
        self.copies[section.id] = kw.get("copy")
        return type("O", (), {
            "code": f"export default function {section.component_name}() "
                    "{ return null; }\n",
            "usage": type("U", (), {"cost": lambda *_a, **_k: 0.0})(),
        })()


def test_the_builder_is_handed_the_answered_copy_not_a_fresh_invention(
    run, editor, monkeypatch
):
    from conftest import install_build
    from sparrow.steps import step_build

    _drain(step_content(run))
    record_content_answers(run, {"hero-1": "Trusted by 12 teams"})

    builder = CopyRecordingBuilder()
    install_build(monkeypatch, builder, blueprints=BLUEPRINTS)
    _drain(step_build(run))

    # The whole chain: drafted, questioned, answered, and delivered verbatim.
    assert builder.copies["hero"]["headline"] == "Trusted by 12 teams"
    assert builder.copies["nav"]["brand_label"] == "Ledgerline"


def test_a_section_with_no_drafted_copy_still_builds(run, monkeypatch):
    """A project from before this stage existed has no content.json at all."""
    from conftest import install_build
    from sparrow.steps import step_build

    builder = CopyRecordingBuilder()
    install_build(monkeypatch, builder, blueprints=BLUEPRINTS)
    _drain(step_build(run))
    assert builder.copies["hero"] is None

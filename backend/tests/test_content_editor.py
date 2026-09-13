"""The content editor drafts every slot and asks about almost none of them.

Two failure directions, and the parser has to hold both. A slot the model skips
becomes an empty element that the inspector reports as a visual defect two stages
and several dollars downstream, so a hole must fail here. An ask against a slot
that does not exist cannot be rendered beside its draft, so it must be dropped
rather than shown as a blank box with a heading.

No model calls. The agent's own `call` is replaced, because what is under test is
the contract between the model's JSON and the rest of the run.
"""

from __future__ import annotations

import json

import pytest

from sparrow.agents.content_editor import Ask, ContentEditor, Copy, Source, _parse
from sparrow.blackboard.schema import Blueprint, Brief, Constraint

BLUEPRINT = Blueprint(
    id="hero",
    purpose="Introduce the product and give the reader one action.",
    slots=["eyebrow", "headline", "body", "primary_cta_label", "features[]"],
    structure="stacked",
)

BRIEF = Brief(
    product_name="Worktree",
    category="Developer tool",
    offering="An open-source IDE that uses AI agents to change code safely.",
    audience="Professional software engineers in unfamiliar codebases.",
    tone="Technically credible, restrained.",
    primary_action="Download or try the IDE",
)


def _payload(**over) -> str:
    body = {
        "slots": {
            "eyebrow": "WORKTREE",
            "headline": "Understand the code. Control the change.",
            "body": "we are opensource, released under apche 2.0",
            "primary_cta_label": "Try the IDE",
            "features[]": ["Scoped edits", "Reviewable diffs"],
        },
        "source": {
            "eyebrow": "drafted",
            "headline": "drafted",
            "body": "constraint",
            "primary_cta_label": "drafted",
            "features[]": "drafted",
        },
        "asks": [],
    }
    body.update(over)
    return json.dumps(body)


CONSTRAINTS = [Constraint(id="c1",
                          text="we are opensource, released under apche 2.0")]


def _parsed(text: str, source_slots=None, constraints=None) -> Copy:
    return _parse(text, "hero", BLUEPRINT, source_slots or {},
                  CONSTRAINTS if constraints is None else constraints)


# ---------------------------------------------------------------- the contract

def test_every_slot_is_filled_and_attributed():
    c = _parsed(_payload())
    assert set(c.slots) == set(BLUEPRINT.slots)
    assert c.slots["features[]"] == ["Scoped edits", "Reviewable diffs"]
    assert c.asks == []


def test_a_verbatim_constraint_keeps_its_own_spelling_and_is_marked():
    c = _parsed(_payload())
    # "apche" is the user's typo. §4: a constraint is never reworded, and the
    # provenance is what stops a later pass from tidying it.
    assert c.slots["body"] == "we are opensource, released under apche 2.0"
    assert c.provenance["body"] is Source.CONSTRAINT
    assert c.provenance["headline"] is Source.DRAFTED


def test_a_constraint_claim_is_verified_against_the_real_constraints():
    """The model marks a slot "constraint" after rewriting it. Measured on the
    real ide blueprints: a hero body came back labelled `constraint` carrying
    the model's own sentence, and a testimonial headline came back labelled
    `constraint` holding a different constraint pasted where it did not belong.
    Believing the label would exempt our invented prose from ever being
    redrafted — the one direction §4 cannot tolerate."""
    payload = json.loads(_payload())
    payload["slots"]["body"] = "We are open source, released under Apache 2.0."
    c = _parsed(json.dumps(payload))
    # Tidied spelling and capitalisation. Close, and therefore exactly wrong.
    assert c.provenance["body"] is Source.DRAFTED


def test_whitespace_alone_does_not_break_a_genuine_constraint_match():
    payload = json.loads(_payload())
    payload["slots"]["body"] = "we are opensource,  released under apche 2.0"
    assert _parsed(json.dumps(payload)).provenance["body"] is Source.CONSTRAINT


def test_an_unknown_source_value_falls_back_to_drafted():
    # Claiming a slot is the user's words when it is ours is the dangerous
    # direction: it would protect invented copy from being redrafted later.
    c = _parsed(_payload(source={**json.loads(_payload())["source"],
                                "headline": "user_supplied"}))
    assert c.provenance["headline"] is Source.DRAFTED


def test_a_missing_slot_fails_here_rather_than_downstream():
    slots = json.loads(_payload())["slots"]
    del slots["body"]
    with pytest.raises(ValueError, match="left slot 'body' empty"):
        _parsed(_payload(slots=slots))


def test_no_json_at_all_is_an_error_not_an_empty_section():
    with pytest.raises(ValueError, match="no JSON"):
        _parsed("I'm sorry, I can't help with that.")


# -------------------------------------------------------------------- the asks

ASK = {"slot": "headline", "question": "How many teams use it today?",
       "invented": "used by 400 teams"}


def test_an_ask_carries_the_draft_and_the_source_example():
    c = _parsed(_payload(asks=[ASK]), source_slots={"headline": "Ship faster."})
    assert len(c.asks) == 1
    a = c.asks[0]
    assert a.draft == "Understand the code. Control the change."
    assert a.invented == "used by 400 teams"
    # §6: the source snippet is shown as reference for what is being requested.
    assert a.source_example == "Ship faster."


def test_an_ask_against_a_slot_that_does_not_exist_is_dropped():
    c = _parsed(_payload(asks=[{**ASK, "slot": "pricing_note"},
                               {**ASK, "question": ""}, ASK]))
    assert [a.slot for a in c.asks] == ["headline"]


def test_a_repeating_slot_ask_shows_the_whole_list_as_its_draft():
    c = _parsed(_payload(asks=[{**ASK, "slot": "features[]"}]))
    assert c.asks[0].draft == "Scoped edits · Reviewable diffs"


# ------------------------------------------------------------- answering an ask

def test_answering_replaces_the_draft_and_marks_the_slot_as_the_users():
    c = _parsed(_payload(asks=[ASK]))
    c.apply(c.asks[0].id, "Used by 12 teams at Acme.")
    assert c.slots["headline"] == "Used by 12 teams at Acme."
    assert c.provenance["headline"] is Source.USER_SUPPLIED
    assert c.unanswered() == []


def test_answering_an_ask_twice_is_refused():
    c = _parsed(_payload(asks=[ASK]))
    c.apply(c.asks[0].id, "Used by 12 teams.")
    with pytest.raises(KeyError):
        c.apply("hero-1", "again")


# ---------------------------------------------------------------- the API call

class _Reply:
    def __init__(self, text: str) -> None:
        self.text = text


class _Provider:
    """Accepts the `_agent_name` the base class stamps on it."""

    _agent_name = ""


def test_write_sends_the_constraints_and_the_source_example(monkeypatch):
    seen: dict[str, str] = {}

    def fake_call(self, *, system, user, images=None):
        seen["system"], seen["user"] = system, user
        return _Reply(_payload())

    monkeypatch.setattr(ContentEditor, "call", fake_call)
    ed = ContentEditor(provider=_Provider())
    c = ed.write(
        BRIEF,
        [Constraint(id="c1", text="we are opensource, released under apche 2.0")],
        BLUEPRINT,
        section_id="hero",
        source_slots={"headline": "Ship faster."},
    )

    assert c.section_id == "hero"
    assert "apche 2.0" in seen["user"]          # verbatim, typo intact
    assert "Worktree" in seen["user"]           # product_name reaches the copy
    assert "Ship faster." in seen["user"]
    assert "features[]" in seen["user"]


def test_a_run_with_no_constraints_sends_no_constraint_block(monkeypatch):
    seen: dict[str, str] = {}
    monkeypatch.setattr(
        ContentEditor, "call",
        lambda self, *, system, user, images=None: (
            seen.update(user=user), _Reply(_payload()))[1],
    )
    ContentEditor(provider=_Provider()).write(
        BRIEF, [], BLUEPRINT, section_id="hero")
    assert "hard_constraints" not in seen["user"]

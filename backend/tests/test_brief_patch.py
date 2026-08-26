"""A name must be correctable on a project that is already built.

Gate 1 is where the name is settled, and `record_product_name` is reachable only
while that gate is open. All eight projects built before the name existed carry
`product_name: ""` with no way to fix it short of a full re-run — the wrong
price for one string, and the reason the voice-ai site shipped a hero reading
"Off-Hook".
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from conftest import make_run
from sparrow.blackboard.schema import Blackboard


@pytest.fixture
def client(tmp_path, monkeypatch):
    import sparrow.api as api
    # The API caches a Run per project id for the process lifetime. Without
    # clearing it, the second test in this file talks to the first test's
    # tmp_path and silently writes nowhere useful.
    api._RUNS.clear()
    make_run(tmp_path, {"hero": "x"}, pid="p1")
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    return TestClient(api.app)


def _name(tmp_path) -> str:
    bb = Blackboard.model_validate_json(
        (tmp_path / "projects/p1/blackboard.json").read_text())
    return bb.brief.product_name


def test_the_name_is_settled_and_recorded(client, tmp_path):
    r = client.patch("/projects/p1/brief", json={"product_name": "voiceowl.ai"})
    assert r.status_code == 200
    assert r.json()["product_name"] == "voiceowl.ai"
    assert _name(tmp_path) == "voiceowl.ai"


def test_the_correction_leaves_a_decision_behind(client, tmp_path):
    client.patch("/projects/p1/brief", json={"product_name": "voiceowl.ai"})
    bb = Blackboard.model_validate_json(
        (tmp_path / "projects/p1/blackboard.json").read_text())
    # §3: a state transition nobody recorded is a run nobody can replay.
    assert any("voiceowl.ai" in d.summary for d in bb.decisions)


def test_a_blank_name_is_refused_not_stored(client, tmp_path):
    before = _name(tmp_path)
    r = client.patch("/projects/p1/brief", json={"product_name": "   "})
    # Defaulting a blank would put the project straight back into the "not
    # given" branch that produced Off-Hook in the first place.
    assert r.status_code == 400
    assert _name(tmp_path) == before


def test_whitespace_is_normalised(client, tmp_path):
    client.patch("/projects/p1/brief", json={"product_name": "  voice   owl.ai "})
    assert _name(tmp_path) == "voice owl.ai"


def test_an_unknown_project_is_404(client):
    assert client.patch("/projects/nope/brief",
                        json={"product_name": "x"}).status_code == 404


def test_the_response_says_the_imagery_is_now_stale(client):
    # A corrected name with stale imagery is still two companies on one page.
    r = client.patch("/projects/p1/brief", json={"product_name": "voiceowl.ai"})
    assert "rebuild" in r.json()["next"]

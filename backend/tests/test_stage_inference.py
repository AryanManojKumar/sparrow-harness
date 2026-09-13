"""A finished project must not report that it has not started.

`Blackboard.stage` defaults to "brief" and stage persistence only landed
recently, so every project built before it carried that default — nine finished
sites all claiming they were at the beginning. Clicking one made the next
/advance re-extract every reference site and re-run the whole pipeline: a full
run's cost, spent on a project that was already built.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import make_run
from sparrow.blackboard.schema import Blackboard
from sparrow.blackboard.store import Store
from sparrow.orchestrator import Stage


@pytest.fixture
def env(tmp_path, monkeypatch):
    import sparrow.api as api
    api._RUNS.clear()
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    make_run(tmp_path, {"hero": "x"}, pid="p1")
    return api, tmp_path / "projects/p1"


def _export(d):
    out = d / "workspace/out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text("<html></html>")


def test_a_project_with_an_exported_site_resumes_at_the_preview_gate(env):
    api, d = env
    _export(d)
    api._RUNS.clear()
    assert api._run_for("p1").stage is Stage.GATE_PREVIEW


def test_a_project_with_sections_and_a_design_system_resumes_at_build(env):
    api, d = env          # make_run gives both, and writes no export
    api._RUNS.clear()
    assert api._run_for("p1").stage is Stage.BUILD


def test_a_genuinely_new_project_still_starts_at_brief(env, tmp_path):
    """The negative. Inference that fired on an empty project would skip the
    brief entirely and build a site nobody described."""
    api, _ = env
    import json
    d = tmp_path / "projects/fresh"
    d.mkdir(parents=True)
    (d / "blackboard.json").write_text(
        json.dumps({"project_id": "fresh", "version": 0}))
    api._RUNS.clear()
    assert api._run_for("fresh").stage is Stage.BRIEF


def test_a_recorded_stage_always_wins_over_inference(env):
    api, d = env
    _export(d)                       # inference would say gate:preview
    Store(d / "blackboard.json").set_stage("assets")
    api._RUNS.clear()
    # A project that really is mid-assets must not be pushed to the end.
    assert api._run_for("p1").stage is Stage.ASSETS


def test_the_listing_reports_the_same_stage_the_run_resumes_at(env):
    api, d = env
    _export(d)
    api._RUNS.clear()
    c = TestClient(api.app)
    row = next(r for r in c.get("/projects").json() if r["project_id"] == "p1")
    assert row["stage"] == api._run_for("p1").stage.value == "gate:preview"

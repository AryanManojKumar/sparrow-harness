"""A restart must resume, not re-run.

`Run.stage` lived only in memory. Restarting the server sent every project back
to `brief`, and the next /advance re-extracted every reference site — a whole
run's cost, spent silently, on work already done. It happened on a live project:
a rebuild set the stage to `assets`, the server restarted, and the next advance
began at `brief` and went straight into `sources`.

The orchestrator's own docstring claimed a run resumes from where it halted.
Sections and decisions persisted; the pointer to the current stage did not.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import make_run
from sparrow.blackboard.schema import Blackboard
from sparrow.blackboard.store import Store
from sparrow.orchestrator import Stage


@pytest.fixture
def paths(tmp_path, monkeypatch):
    import sparrow.api as api
    api._RUNS.clear()
    make_run(tmp_path, {"hero": "x"}, pid="p1")
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    return api, tmp_path / "projects/p1/blackboard.json"


def test_a_saved_stage_is_restored_on_a_cold_load(paths):
    api, bb_path = paths
    Store(bb_path).set_stage("build")
    api._RUNS.clear()                      # the restart
    assert api._run_for("p1").stage is Stage.BUILD


def test_a_project_that_never_ran_starts_at_the_beginning(paths):
    api, _ = paths
    assert api._run_for("p1").stage is Stage.BRIEF


def test_an_unknown_stage_string_does_not_crash_the_load(paths):
    api, bb_path = paths
    Store(bb_path).set_stage("teleport")   # e.g. a stage renamed since
    api._RUNS.clear()
    # Falling back beats refusing to open the project at all.
    assert api._run_for("p1").stage is Stage.BRIEF


def test_set_stage_does_not_append_a_decision(paths):
    _api, bb_path = paths
    store = Store(bb_path)
    before = len(store.load().decisions)
    store.set_stage("design")
    store.set_stage("build")
    # Eleven rows of "now at build" would bury the decisions a human wants.
    assert len(store.load().decisions) == before


def test_setting_the_same_stage_twice_does_not_rewrite_the_file(paths):
    _api, bb_path = paths
    store = Store(bb_path)
    store.set_stage("build")
    v = store.load().version
    store.set_stage("build")
    assert store.load().version == v


def test_the_pointer_survives_a_real_round_trip(paths):
    _api, bb_path = paths
    Store(bb_path).set_stage("verify")
    assert Blackboard.model_validate_json(bb_path.read_text()).stage == "verify"

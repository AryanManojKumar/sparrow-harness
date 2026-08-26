"""The listing is what a UI navigates from, so its ids must be navigable.

It reported `bb.project_id` — the id written INSIDE the blackboard — while every
URL in this API is keyed by the directory. A project copied from another carries
the original's id, so `_assetgate-live` listed itself as "crossborder-e2e" and
the list showed two rows with one id, either of which opened the wrong project.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from conftest import make_run


@pytest.fixture
def client(tmp_path, monkeypatch):
    import sparrow.api as api
    api._RUNS.clear()
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    return TestClient(api.app), tmp_path


def test_the_id_is_the_directory_not_the_blackboards_own_field(client):
    c, root = client
    make_run(root, {"hero": "x"}, pid="copied-from")
    bb = root / "projects/copied-from/blackboard.json"
    d = json.loads(bb.read_text())
    d["project_id"] = "the-original"          # what a copied project looks like
    bb.write_text(json.dumps(d))

    rows = c.get("/projects").json()
    assert [r["project_id"] for r in rows] == ["copied-from"]


def test_two_projects_never_collapse_to_one_id(client):
    c, root = client
    for pid in ("a", "b"):
        make_run(root, {"hero": "x"}, pid=pid)
        f = root / f"projects/{pid}/blackboard.json"
        d = json.loads(f.read_text())
        d["project_id"] = "same-name-inside"
        f.write_text(json.dumps(d))

    ids = [r["project_id"] for r in c.get("/projects").json()]
    assert sorted(ids) == ["a", "b"]


def test_a_row_says_whether_there_is_anything_to_preview(client):
    c, root = client
    make_run(root, {"hero": "x"}, pid="p1")
    assert c.get("/projects").json()[0]["has_preview"] is False

    out = root / "projects/p1/workspace/out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text("<html></html>")
    assert c.get("/projects").json()[0]["has_preview"] is True


def test_an_unreadable_blackboard_does_not_take_down_the_list(client):
    c, root = client
    make_run(root, {"hero": "x"}, pid="good")
    bad = root / "projects/bad"
    bad.mkdir(parents=True, exist_ok=True)
    (bad / "blackboard.json").write_text('{"nonsense": true}')

    rows = c.get("/projects").json()
    assert len(rows) == 2
    bad_row = next(r for r in rows if r["project_id"] == "bad")
    assert bad_row["readable"] is False
    # Still navigable-ish: the id and the preview flag are known without parsing.
    assert "has_preview" in bad_row


def test_most_recently_touched_comes_first(client):
    import os
    import time
    c, root = client
    for pid in ("older", "newer"):
        make_run(root, {"hero": "x"}, pid=pid)
    f = root / "projects/older/blackboard.json"
    os.utime(f, (time.time() - 9999, time.time() - 9999))

    assert [r["project_id"] for r in c.get("/projects").json()] == ["newer", "older"]

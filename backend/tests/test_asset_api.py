"""The asset gate over HTTP — the part the frontend actually touches.

The gate is worth testing at this level because its answer has a different shape
from every other gate: `assets`, one decision per image, rather than a single
`choice`. A frontend that posts `{"choice": "generate"}` here must be told what
is wrong, not quietly given generated images for everything.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from sparrow import api, telemetry
from sparrow.orchestrator import Stage

from test_asset_gate import blueprint, png, project

PID = "t"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A server rooted in a temp dir, so nothing here touches the real projects
    or appends to the repo's log."""
    run = project(tmp_path, {"hero": ["a dashboard screenshot"],
                             "feature-grid": ["one", "two"]})
    monkeypatch.setattr(api, "ROOT", tmp_path)
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(telemetry, "ROOT", tmp_path)
    monkeypatch.setattr(telemetry, "LOG_DIR", tmp_path / "logs")
    api._RUNS.clear()

    c = TestClient(api.app)
    live = api._run_for(PID)
    live.stage = Stage.GATE_ASSETS          # skip the paid stages ahead of it
    list(live.advance())                     # runs step_asset_gate, halts
    yield c
    api._RUNS.clear()


def test_the_gate_is_visible_with_a_choice_per_image(client):
    r = client.get(f"/projects/{PID}/gate")
    assert r.status_code == 200
    body = r.json()
    assert body["awaiting"] and body["gate"] == "gate:assets"
    assert [o["asset_id"] for o in body["options"]] == [
        "hero-1", "feature-grid-1", "feature-grid-2"]
    assert body["options"][0]["prominence"] == "dominant"
    assert body["options"][0]["choices"][0]["post_file_to"] == \
        f"/projects/{PID}/assets/hero-1"


def test_the_plan_is_readable_on_its_own(client):
    r = client.get(f"/projects/{PID}/assets")
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == ["hero-1", "feature-grid-1", "feature-grid-2"]


def test_uploading_then_answering(client):
    up = client.post(f"/projects/{PID}/assets/hero-1",
                     files={"file": ("dashboard.png", png(), "image/png")})
    assert up.status_code == 200, up.text
    assert up.json()["stored"] == "hero-1.png"

    r = client.post(f"/projects/{PID}/gate", json={"assets": {
        "hero-1": "upload", "feature-grid-1": "generate", "feature-grid-2": "skip"}})
    assert r.status_code == 200, r.text
    assert r.json()["decisions"] == {
        "hero-1": "upload", "feature-grid-1": "generate", "feature-grid-2": "skip"}
    assert r.json()["stage"] == "assets", "the gate must advance to ASSETS"


def test_answering_upload_with_no_file_is_a_400(client):
    r = client.post(f"/projects/{PID}/gate", json={"assets": {
        "hero-1": "upload", "feature-grid-1": "skip", "feature-grid-2": "skip"}})
    assert r.status_code == 400
    assert "no file has been posted" in r.json()["detail"]


def test_a_single_global_choice_is_refused(client):
    """The whole point of the gate. One answer for every image forces a founder
    with one real screenshot to either fabricate the rest or lose it."""
    r = client.post(f"/projects/{PID}/gate", json={"choice": "generate"})
    assert r.status_code == 400
    assert "decided individually" in r.json()["detail"]


def test_a_partial_answer_is_refused(client):
    r = client.post(f"/projects/{PID}/gate", json={"assets": {"hero-1": "skip"}})
    assert r.status_code == 400
    assert "feature-grid-1" in r.json()["detail"]


def test_an_unknown_asset_id_is_refused(client):
    r = client.post(f"/projects/{PID}/gate",
                    json={"assets": {"hero-1": "skip", "hero-9": "skip"}})
    assert r.status_code == 400
    assert "no such asset" in r.json()["detail"]


def test_uploading_to_an_unknown_asset_is_refused(client):
    r = client.post(f"/projects/{PID}/assets/nope-1",
                    files={"file": ("x.png", png(), "image/png")})
    assert r.status_code == 400
    assert "no such asset" in r.json()["detail"]


def test_a_file_that_is_not_an_image_is_refused(client):
    r = client.post(f"/projects/{PID}/assets/hero-1",
                    files={"file": ("x.png", b"not a png", "image/png")})
    assert r.status_code == 400
    assert "not a readable image" in r.json()["detail"]


def test_an_empty_upload_is_refused(client):
    r = client.post(f"/projects/{PID}/assets/hero-1",
                    files={"file": ("x.png", b"", "image/png")})
    assert r.status_code == 400


def test_a_jpeg_is_accepted_and_kept_as_uploaded(client, tmp_path):
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (5, 5, 5)).save(buf, "JPEG")
    r = client.post(f"/projects/{PID}/assets/hero-1",
                    files={"file": ("shot.jpg", buf.getvalue(), "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["stored"] == "hero-1.jpg"

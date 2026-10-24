"""POST /projects/{id}/edit — a pointed instruction against one selected element.

The picker only identifies the element. This is the half that changes the
section file and rebuilds the export, so a click in the preview becomes a
real edit rather than a highlighted box.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import SECTIONS_DIR, make_run
from sparrow import api, telemetry
from sparrow.agents.builder import BuildOutput


PID = "t"


class _Usage:
    def cost(self, *_a, **_k) -> float:
        return 0.01


class FakeEditor:
    tier = None

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.provider = type("P", (), {"name": "fake"})()

    def edit(self, bb, section, code, instruction, element):
        self.calls.append((section.id, instruction, dict(element)))
        return BuildOutput(code.replace("OldBrand", "NewBrand"), None, _Usage())


@pytest.fixture
def editor():
    return FakeEditor()


@pytest.fixture
def client(tmp_path, monkeypatch, editor):
    run = make_run(tmp_path, {"nav": "export default function Nav(){return <span>OldBrand</span>}\n"})
    (run.workspace / "out" / "index.html").write_text("<html><body>x</body></html>")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(telemetry, "ROOT", tmp_path)
    monkeypatch.setattr(telemetry, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr("sparrow.agents.editor.Editor", lambda: editor)
    monkeypatch.setattr("sparrow.cli._run_build", lambda ws: (True, "ok"))
    api._RUNS.clear()
    yield TestClient(api.app), run, editor
    api._RUNS.clear()


def test_blank_instruction_is_refused(client):
    c, _, _ = client
    r = c.post(f"/projects/{PID}/edit", json={"instruction": "  ", "element": {"section_id": "nav"}})
    assert r.status_code == 400


def test_unknown_section_is_refused(client):
    c, _, _ = client
    r = c.post(f"/projects/{PID}/edit", json={
        "instruction": "make it red",
        "element": {"section_id": "pricing"},
    })
    assert r.status_code == 400
    assert "pricing" in r.json()["detail"]


def test_edit_rewrites_the_section_and_rebuilds(client):
    c, run, editor = client
    r = c.post(f"/projects/{PID}/edit", json={
        "instruction": "rename OldBrand to NewBrand",
        "element": {
            "tag": "span",
            "text": "OldBrand",
            "section_id": "nav",
            "selector": "section#nav span",
            "file_hint": "src/components/sections/Nav.tsx",
        },
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["section"] == "nav"
    assert body["rebuilt"] is True
    written = (run.workspace / SECTIONS_DIR / "Nav.tsx").read_text()
    assert "NewBrand" in written
    assert "OldBrand" not in written
    assert editor.calls and editor.calls[0][0] == "nav"
    assert editor.calls[0][1] == "rename OldBrand to NewBrand"


def test_edit_resolves_a_section_from_file_hint_when_id_is_missing(client):
    c, run, _ = client
    r = c.post(f"/projects/{PID}/edit", json={
        "instruction": "rename OldBrand to NewBrand",
        "element": {"tag": "span", "text": "OldBrand",
                    "file_hint": "src/components/sections/Nav.tsx"},
    })
    assert r.status_code == 200, r.text
    assert "NewBrand" in (run.workspace / SECTIONS_DIR / "Nav.tsx").read_text()


def test_edit_refuses_while_a_run_is_advancing(client, monkeypatch):
    c, _, _ = client
    api._ADVANCING.add(PID)
    try:
        r = c.post(f"/projects/{PID}/edit", json={
            "instruction": "rename it",
            "element": {"section_id": "nav"},
        })
        assert r.status_code == 409
    finally:
        api._ADVANCING.discard(PID)

"""The preview iframe is a different origin from the console.

The parent page cannot read the framed document, so a picker has to be injected
into the HTML the preview serves. These tests lock that contract: HTML gets the
runtime, other files do not, and a section id maps to the file the builder wrote.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sparrow import api, telemetry
from sparrow.picker import file_hint, inject_picker


def test_inject_picker_inserts_the_runtime_before_body_close():
    out = inject_picker("<html><body><h1>hi</h1></body></html>")
    assert 'data-sparrow-picker-runtime="1"' in out
    assert out.index("data-sparrow-picker-runtime") < out.index("</body>")
    assert 'src="/static/picker.js"' in out


def test_inject_picker_is_idempotent():
    once = inject_picker("<html><body></body></html>")
    twice = inject_picker(once)
    assert twice.count("data-sparrow-picker-runtime") == 1


def test_inject_picker_appends_when_there_is_no_body_tag():
    out = inject_picker("<html><h1>hi</h1></html>")
    assert 'data-sparrow-picker-runtime="1"' in out


def test_file_hint_follows_the_builder_section_path():
    assert file_hint("nav") == "src/components/sections/Nav.tsx"
    assert file_hint("feature-grid") == "src/components/sections/FeatureGrid.tsx"
    assert file_hint("product-showcase") == "src/components/sections/ProductShowcase.tsx"


@pytest.fixture
def client(tmp_path, monkeypatch):
    out = tmp_path / "projects" / "p1" / "workspace" / "out"
    out.mkdir(parents=True)
    (out / "index.html").write_text(
        "<html><body><section id='nav'><span>Brand</span></section></body></html>")
    (out / "app.css").write_text("body{color:red}")
    monkeypatch.setattr(api, "ROOT", tmp_path)
    monkeypatch.setattr(api, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(telemetry, "ROOT", tmp_path)
    monkeypatch.setattr(telemetry, "LOG_DIR", tmp_path / "logs")
    api._RUNS.clear()
    yield TestClient(api.app)
    api._RUNS.clear()


def test_preview_html_includes_the_picker_runtime(client):
    r = client.get("/projects/p1/preview/")
    assert r.status_code == 200
    assert 'data-sparrow-picker-runtime="1"' in r.text
    assert "Brand" in r.text


def test_preview_html_at_index_path_also_includes_the_runtime(client):
    r = client.get("/projects/p1/preview/index.html")
    assert r.status_code == 200
    assert 'data-sparrow-picker-runtime="1"' in r.text


def test_preview_does_not_inject_into_non_html(client):
    r = client.get("/projects/p1/preview/app.css")
    assert r.status_code == 200
    assert "sparrow-picker" not in r.text
    assert r.text == "body{color:red}"


def test_picker_script_is_served_and_names_the_message_channel(client):
    r = client.get("/static/picker.js")
    assert r.status_code == 200
    body = r.text
    assert 'channel: "sparrow"' in body or "channel: 'sparrow'" in body
    assert "element-select" in body
    assert "select-enable" in body

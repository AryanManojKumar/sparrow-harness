"""The free check that would have saved three paid rounds.

`PageReport.failed_requests` was collected from the first version of the capture
code and nothing ever read it. When previews moved to Next's `basePath` and the
static server kept serving the export at "/", every asset URL 404'd: no
stylesheet, no JS, Times New Roman on white, every Motion section frozen at its
initial opacity. The inspector then honestly reported collisions and faded text,
the fixer read a source file that was completely fine and disputed, and the loop
spent its whole budget arguing about a screenshot of a page nobody would ever
see.

The guard costs nothing — the number is already in hand before the first model
call. These tests hold it from both sides: it must stop the round on a 404 and
must NOT stop a page that merely has defects.
"""

from __future__ import annotations

import contextlib

import pytest

from sparrow import steps
from sparrow.capture import PageReport
from sparrow.orchestrator import Stage

from conftest import SECTIONS_DIR, RecordingFixer, drain, make_run

CLEAN = 'export default function Hero() { return <section className="gap-8" />; }\n'


def report(failed: list[str]) -> PageReport:
    return PageReport(console_errors=[], failed_requests=failed,
                      horizontal_overflow=[], fold_fade=[], spill=[],
                      contrast_failures=[], sections=[])


class ForbiddenInspector:
    """Constructing this is the failure. Every call it makes costs money."""

    def __init__(self) -> None:
        raise AssertionError(
            "the inspector was constructed on a page that could not load its "
            "own assets — that is a paid opinion about a page nobody will see"
        )


class CountingInspector:
    tier = "fake"

    def __init__(self) -> None:
        CountingInspector.built += 1

    built = 0


def stub_capture(monkeypatch, reports):
    import sparrow.capture as capture

    @contextlib.contextmanager
    def serve(_directory, port=4321):
        yield f"http://localhost:{port}/"

    monkeypatch.setattr(capture, "serve", serve)
    monkeypatch.setattr(capture, "inspect_page", lambda _url, _out: reports)


def prepared(tmp_path):
    run = make_run(tmp_path, {"hero": CLEAN})
    (run.workspace / "out" / "index.html").write_text("<html></html>")
    return run


# ------------------------------------------------------------------ positive


def test_a_failed_request_stops_the_round_before_the_inspector(tmp_path, monkeypatch):
    import sparrow.agents.inspector as inspector_mod

    run = prepared(tmp_path)
    stub_capture(monkeypatch, {"desktop": report(["/_next/static/css/app.css"])})
    monkeypatch.setattr(inspector_mod, "Inspector", ForbiddenInspector)

    with pytest.raises(steps.AssetsNotServed) as e:
        steps._inspect_once(run, None, {}, port=4611)
    assert "/_next/static/css/app.css" in str(e.value)


def test_the_verify_loop_reports_the_failed_urls_and_does_not_ask_to_ship_blind(
        tmp_path, monkeypatch):
    import sparrow.agents.builder as builder_mod
    import sparrow.agents.inspector as inspector_mod
    import sparrow.blueprints as blueprints_mod
    import sparrow.cli as cli_mod

    run = prepared(tmp_path)
    failed = [f"/_next/static/chunks/{i}.js" for i in range(24)]
    stub_capture(monkeypatch, {"desktop": report(failed)})
    monkeypatch.setattr(inspector_mod, "Inspector", ForbiddenInspector)
    fixer = RecordingFixer()
    monkeypatch.setattr(builder_mod, "Fixer", lambda: fixer)
    monkeypatch.setattr(blueprints_mod, "load_dir", lambda _d: {})
    monkeypatch.setattr(cli_mod, "_run_build", lambda _ws: (True, "ok"))

    events, gate = drain(steps.step_verify(run))

    blocked = [e for e in events if e.kind == "blocked"]
    assert blocked, "a round stopped for a 404 must say so"
    assert "not serving its own assets" in blocked[0].message
    assert "24 request(s) failed" in blocked[0].message

    assert fixer.calls == [], "nothing may be fixed from a page that never loaded"
    assert gate is not None and gate.gate is Stage.GATE_PREVIEW
    # It must not read as "0 visual defects, ship it" — that is the reading the
    # bug produced, and it is the opposite of the truth.
    assert "not serving 24 of its own files" in gate.question, gate.question
    assert gate.question.index("not serving") < gate.question.index("drift finding"), \
        "the broken preview has to lead the question, not trail it"


# ------------------------------------------------------------------ negative


def test_a_page_that_loads_is_inspected_normally(tmp_path, monkeypatch):
    """The negative. A guard that stops a healthy page stops every page."""
    import sparrow.agents.inspector as inspector_mod

    run = prepared(tmp_path)
    stub_capture(monkeypatch, {"desktop": report([])})
    CountingInspector.built = 0
    monkeypatch.setattr(inspector_mod, "Inspector", CountingInspector)

    bb = steps._bb(run)
    page_level, per_section, cost = steps._inspect_once(run, bb, {}, port=4612)

    assert CountingInspector.built == 1, "a healthy page must still reach the inspector"
    assert page_level == [] and per_section == {} and cost == 0.0


def test_console_errors_alone_do_not_stop_the_round(tmp_path, monkeypatch):
    """Only a FAILED REQUEST means the page is not the page. A console error is a
    real defect the inspector and the fixer can act on, and stopping on one would
    disable the loop this stage exists to run."""
    import sparrow.agents.inspector as inspector_mod

    run = prepared(tmp_path)
    stub_capture(monkeypatch, {"desktop": PageReport(
        console_errors=["TypeError: undefined is not a function"], failed_requests=[],
        horizontal_overflow=[], fold_fade=[], spill=[], contrast_failures=[],
        sections=[])})
    CountingInspector.built = 0
    monkeypatch.setattr(inspector_mod, "Inspector", CountingInspector)

    bb = steps._bb(run)
    page_level, _per_section, _cost = steps._inspect_once(run, bb, {}, port=4613)
    assert [d.code for d in page_level] == ["console-error"]

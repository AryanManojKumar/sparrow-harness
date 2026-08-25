"""Two bugs in `steps.step_verify`, each pinned by a test that fails without the fix.

BUG A — drift findings were computed and discarded. `audit_dir` ran at the top of
every round, its findings were counted into the progress line and into the gate
question, and then only `per_section` (the inspector's visual defects) was passed
to the fixer. So the same 31 off-scale-gap findings were reported round after
round and never fixed, and gate 3 asked "ship it?" while holding a list nothing
had acted on.

BUG B — "a fix broke the build — reverting to the last good export" did not revert.
The loop emitted that sentence and broke. Nothing restored the section files, so
the workspace was left with the code that had just failed to build, while the
message claimed recovery.

Both are proved the same way: replace the expensive collaborators with recorders
and look at what they actually received and at what is actually on disk. No model
call, no browser.
"""

from __future__ import annotations

import pytest

from sparrow import steps
from sparrow.agents.inspector import Defect
from sparrow.audit import audit_dir
from sparrow.fixtures.ledgerline import DESIGN_SYSTEM
from sparrow.orchestrator import Stage

from conftest import SECTIONS_DIR, RecordingFixer, drain, make_run

# gap-7 is off the declared scale (gap-8 / gap-3) and font-bold is off the
# declared weights (400/500/600). Both are drift the audit finds and the
# inspector cannot see — it is looking at a picture, and no picture
# distinguishes gap-7 from gap-8.
DRIFTY = """export default function Hero() {
  return (
    <section className="flex gap-7">
      <h1 className="font-bold">Continuous evidence</h1>
    </section>
  );
}
"""

CLEAN = """export default function Hero() {
  return (
    <section className="flex gap-8">
      <h1 className="font-semibold">Continuous evidence</h1>
    </section>
  );
}
"""

BREAKS_THE_BUILD = """export default function Hero(
  return ( <section className="flex gap-8" /> );
}
"""


def install(monkeypatch, fixer, *, inspect=None, build=None):
    """Swap out everything in `step_verify` that costs money or opens a browser."""
    import sparrow.agents.builder as builder_mod
    import sparrow.blueprints as blueprints_mod
    import sparrow.cli as cli_mod

    monkeypatch.setattr(builder_mod, "Fixer", lambda: fixer)
    monkeypatch.setattr(blueprints_mod, "load_dir", lambda _d: {})
    monkeypatch.setattr(steps, "_inspect_once",
                        inspect or (lambda *_a, **_k: ([], {}, 0.0)))
    monkeypatch.setattr(cli_mod, "_run_build", build or (lambda _ws: (True, "ok")))


def seeing(defects_by_section):
    """An `_inspect_once` that always reports the same visual defects."""
    return lambda *_a, **_k: ([], {k: list(v) for k, v in defects_by_section.items()}, 0.0)


CLIPPED = Defect("high", "text-clipped", "the headline is clipped", "hero @ 390px", "vision")


# --------------------------------------------------------------------- bug A


def test_drift_findings_reach_the_fixer(tmp_path, monkeypatch):
    """The bug: audit_dir finds real drift and the fixer is handed none of it."""
    run = make_run(tmp_path, {"hero": DRIFTY})

    found = audit_dir(run.workspace / SECTIONS_DIR, DESIGN_SYSTEM)
    assert {f.category for f in found} == {"off-scale-gap", "off-scale-weight"}, \
        "the fixture must actually drift, or the test proves nothing"

    fixer = RecordingFixer(replies={"hero": CLEAN})
    install(monkeypatch, fixer)
    events, gate = drain(steps.step_verify(run))

    assert fixer.calls, (
        "the fixer was never called. audit_dir found drift, the progress line "
        "counted it, and nothing was handed on — that is bug A"
    )
    assert fixer.codes() >= {"off-scale-gap", "off-scale-weight"}, \
        f"drift did not reach the fixer; it got {fixer.codes()}"

    # And the round actually resolved it, rather than reporting it forever.
    assert (run.workspace / SECTIONS_DIR / "Hero.tsx").read_text() == CLEAN
    assert gate is not None and gate.gate is Stage.GATE_PREVIEW
    assert "0 drift finding(s)" in gate.question, gate.question


def test_drift_defects_carry_the_file_and_line_they_were_measured_at(tmp_path, monkeypatch):
    """A defect the fixer cannot locate is a defect it will guess at."""
    run = make_run(tmp_path, {"hero": DRIFTY})
    fixer = RecordingFixer(replies={"hero": CLEAN})
    install(monkeypatch, fixer)
    drain(steps.step_verify(run))

    drift = [d for _sid, ds in fixer.calls for d in ds if d.source == "computed"]
    assert drift
    for d in drift:
        assert "Hero.tsx:" in d.where, d.where
        assert d.severity in {"high", "medium", "low"}
    # The permitted set travels with the finding, from the same DesignSystem the
    # audit derived it from — otherwise the fixer replaces one off-scale value
    # with another off-scale value.
    gap = next(d for d in drift if d.code == "off-scale-gap")
    assert "gap-8" in gap.what and "gap-3" in gap.what, gap.what
    weight = next(d for d in drift if d.code == "off-scale-weight")
    assert "font-semibold" in weight.what, weight.what


def test_a_clean_section_produces_no_drift_and_no_fixer_call(tmp_path, monkeypatch):
    """The negative. A check that never stays quiet is a check nobody can act on."""
    run = make_run(tmp_path, {"hero": CLEAN})

    assert audit_dir(run.workspace / SECTIONS_DIR, DESIGN_SYSTEM) == []

    fixer = RecordingFixer()
    install(monkeypatch, fixer)
    _events, gate = drain(steps.step_verify(run))

    assert fixer.calls == [], "a clean section must not be sent to the fixer"
    assert "0 drift finding(s)" in gate.question
    assert (run.workspace / SECTIONS_DIR / "Hero.tsx").read_text() == CLEAN


def test_drift_is_routed_to_the_section_that_owns_the_file(tmp_path, monkeypatch):
    """Two sections, one drifting. The other must not be touched."""
    run = make_run(tmp_path, {"hero": CLEAN, "cta": DRIFTY.replace("Hero", "Cta")})
    fixer = RecordingFixer(replies={"cta": CLEAN.replace("Hero", "Cta")})
    install(monkeypatch, fixer)
    drain(steps.step_verify(run))

    assert [sid for sid, _ in fixer.calls] == ["cta"], \
        f"drift was routed to the wrong section: {[s for s, _ in fixer.calls]}"


def test_drift_and_visual_defects_arrive_in_one_call_per_section(tmp_path, monkeypatch):
    """One fixer call per section per round, not two — a second pass over the same
    file would be fixing code the first pass had already rewritten.

    The stub inspector stops reporting once the file is fixed, the way a real one
    does. A stub that reports forever makes the loop run its full three rounds and
    says nothing about how many calls a round issues.
    """
    run = make_run(tmp_path, {"hero": DRIFTY})
    path = run.workspace / SECTIONS_DIR / "Hero.tsx"

    def inspect(*_a, **_k):
        still_broken = "gap-7" in path.read_text()
        return [], ({"hero": [CLIPPED]} if still_broken else {}), 0.0

    fixer = RecordingFixer(replies={"hero": CLEAN})
    install(monkeypatch, fixer, inspect=inspect)
    drain(steps.step_verify(run))

    assert len(fixer.calls) == 1, f"{len(fixer.calls)} calls for one section in one round"
    _sid, defects = fixer.calls[0]
    assert {d.source for d in defects} == {"computed", "vision"}
    # Drift first: it names a file and a line, which orients the fixer before it
    # reads a description of something merely seen.
    assert defects[0].source == "computed" and defects[-1].source == "vision"


# --------------------------------------------------------------------- bug B


def _build_reflecting_disk(run, log):
    """A build that fails exactly when the broken code is on disk.

    Canned `(False, ...)` would let a revert that never happened still pass, so
    the fake reads the file the same way pnpm would.
    """
    path = run.workspace / SECTIONS_DIR / "Hero.tsx"

    def build(_ws):
        ok = "export default function Hero(\n" not in path.read_text()
        log.append(ok)
        return ok, "ok" if ok else "./src/components/sections/Hero.tsx\nSyntax error"

    return build


def test_a_fix_that_breaks_the_build_is_reverted(tmp_path, monkeypatch):
    """The bug: the loop said it reverted and left the broken file on disk."""
    run = make_run(tmp_path, {"hero": CLEAN})
    log: list[bool] = []
    fixer = RecordingFixer(replies={"hero": BREAKS_THE_BUILD})
    install(monkeypatch, fixer, inspect=seeing({"hero": [CLIPPED]}),
            build=_build_reflecting_disk(run, log))

    events, gate = drain(steps.step_verify(run))

    on_disk = (run.workspace / SECTIONS_DIR / "Hero.tsx").read_text()
    assert on_disk == CLEAN, (
        "the workspace still holds the fix that broke the build. The run said "
        "'reverting to the last good export' and reverted nothing — that is bug B"
    )
    assert log == [False, True], (
        f"expected a failing build then a confirming rebuild after the revert, got {log}"
    )
    said = " ".join(e.message for e in events)
    assert "revert" in said.lower(), said
    assert gate is not None


def test_a_fix_that_builds_is_kept(tmp_path, monkeypatch):
    """The negative. Reverting a GOOD fix would quietly undo every repair."""
    run = make_run(tmp_path, {"hero": DRIFTY})
    log: list[bool] = []
    fixer = RecordingFixer(replies={"hero": CLEAN})
    install(monkeypatch, fixer, inspect=seeing({"hero": [CLIPPED]}),
            build=_build_reflecting_disk(run, log))

    drain(steps.step_verify(run))

    assert (run.workspace / SECTIONS_DIR / "Hero.tsx").read_text() == CLEAN
    assert False not in log, "a build that succeeded must not trigger a revert"


def test_a_revert_that_does_not_restore_the_build_is_reported_not_swallowed(
        tmp_path, monkeypatch):
    """If the workspace still will not build, the run must fail rather than reach
    gate 3 and ask a human to ship something that does not compile."""
    run = make_run(tmp_path, {"hero": CLEAN})
    fixer = RecordingFixer(replies={"hero": BREAKS_THE_BUILD})
    install(monkeypatch, fixer, inspect=seeing({"hero": [CLIPPED]}),
            build=lambda _ws: (False, "./src/components/sections/Hero.tsx\nSyntax error"))

    with pytest.raises(RuntimeError, match="does not build"):
        drain(steps.step_verify(run))

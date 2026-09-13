"""The blackboard did not record the half of the run that does the work.

Measured across all six projects with a finished, exported build, every section
on every one read `status=pending, attempts=0, defects=0` and `decisions` was
empty — on projects that built, ran three verify rounds and serve a working
preview. `version` climbed, because brief/sources/design went through the old
`_save`, which bumped the number and dumped the model over the file. Nothing
wrote section state and nothing wrote the decision log, so:

  * a run that died mid-build left a record saying it had never started;
  * a re-advance rebuilt sections that were already on disk, at full price;
  * four Fixer disputes that burned three rounds and ~$2 left no trace of what
    had been disputed, so there was nothing to diagnose afterwards.

Every check below has a negative. Three deterministic checks in this project
were confidently wrong before someone tested them against a case that should
fail, and a test that only proves the happy path is not evidence.

No model call, no browser, no pnpm.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparrow import steps
from sparrow.agents.inspector import Defect
from sparrow.blackboard.schema import (Blackboard, BuildStatus, Decision,
                                       DesignSystem)
from sparrow.blackboard.store import Applied, Rejected, Store
from sparrow.fixtures.ledgerline import DESIGN_SYSTEM

from conftest import (SECTIONS_DIR, RecordingBuilder, RecordingFixer,
                      blueprints_for, drain, install_build, make_run, read_bb)

THREE = {"nav": "", "hero": "", "footer": ""}


def build_run(tmp_path, monkeypatch, builder=None, files=None):
    files = files or dict(THREE)
    run = make_run(tmp_path, files)
    builder = builder or RecordingBuilder()
    install_build(monkeypatch, builder, blueprints=blueprints_for(*files))
    return run, builder


# ------------------------------------------------------- state as it happens


def test_section_state_is_on_disk_during_the_build_not_only_after(tmp_path, monkeypatch):
    """The record has to be true at every instant, not only at the end.

    Snapshot taken from inside the builder call for the LAST section: by then
    the two before it must already read BUILT on disk. A stage that saved once
    at the end passes an after-the-fact assertion and fails this one.
    """
    seen: dict[str, list[tuple[str, str, int]]] = {}
    run_box: list = []

    def snapshot(section):
        bb = read_bb(run_box[0])
        seen[section.id] = [(s.id, s.status.value, s.attempts) for s in bb.sections]

    run, builder = build_run(tmp_path, monkeypatch, RecordingBuilder(on_build=snapshot))
    run_box.append(run)
    drain(steps.step_build(run))

    assert seen["footer"] == [("nav", "built", 1), ("hero", "built", 1),
                              ("footer", "pending", 0)], seen["footer"]
    # And the section being built is not marked built before its file exists.
    assert seen["hero"][1] == ("hero", "pending", 0)


def test_a_build_killed_part_way_leaves_an_accurate_partial_record(tmp_path, monkeypatch):
    """The bug, stated directly: nine sections reading `pending` on a page that built.

    The builder dies on the third section. What must survive is the truth — two
    built, one not — rather than either extreme the old code produced (nothing
    recorded at all).
    """
    def die(section):
        if section.id == "footer":
            raise RuntimeError("provider dropped the connection")

    run, builder = build_run(tmp_path, monkeypatch, RecordingBuilder(on_build=die))
    with pytest.raises(RuntimeError, match="dropped the connection"):
        drain(steps.step_build(run))

    bb = read_bb(run)
    assert [(s.id, s.status.value, s.attempts) for s in bb.sections] == [
        ("nav", "built", 1), ("hero", "built", 1), ("footer", "pending", 0)]
    # The files agree with the record — that is the point of writing per section.
    for s in bb.sections:
        assert (run.workspace / s.target_path).exists() == (s.status is BuildStatus.BUILT) \
            or s.id == "footer"


def test_nothing_is_recorded_for_a_section_that_was_never_reached(tmp_path, monkeypatch):
    """The negative. A record that marks everything built the moment the stage
    starts would satisfy the test above just as well and be a worse lie than the
    one it replaces."""
    def die(section):
        raise RuntimeError("dies on the very first section")

    run, _ = build_run(tmp_path, monkeypatch, RecordingBuilder(on_build=die))
    with pytest.raises(RuntimeError):
        drain(steps.step_build(run))

    bb = read_bb(run)
    assert all(s.status is BuildStatus.PENDING and s.attempts == 0 for s in bb.sections)
    assert bb.version == 0, "a build that built nothing must not move the blackboard"


# ----------------------------------------------------------------- no prior state


def test_a_first_run_builds_every_section_exactly_once_in_sitemap_order(
        tmp_path, monkeypatch):
    """Persistence is an addition. A run with no prior state must produce exactly
    what it produced before — same sections, same order, same number of calls."""
    run, builder = build_run(tmp_path, monkeypatch)
    events, _ = drain(steps.step_build(run))

    assert builder.calls == ["nav", "hero", "footer"]
    assert not any("already built" in e.message for e in events), \
        "a first run must not report skipping anything"
    for s in read_bb(run).sections:
        assert s.status is BuildStatus.BUILT and s.attempts == 1


# ---------------------------------------------------------------------- resume


def test_a_second_advance_skips_sections_that_are_already_built(tmp_path, monkeypatch):
    run, first = build_run(tmp_path, monkeypatch)
    drain(steps.step_build(run))
    assert first.calls == ["nav", "hero", "footer"]

    second = RecordingBuilder()
    install_build(monkeypatch, second, blueprints=blueprints_for(*THREE))
    events, _ = drain(steps.step_build(run))

    assert second.calls == [], (
        "a resumed build re-ran the builder over sections that were already on "
        "disk — that is a full-price rebuild of work already paid for")
    assert sum("already built" in e.message for e in events) == 3


def test_resume_rebuilds_only_what_did_not_finish(tmp_path, monkeypatch):
    """The partial case: two built, one not. Exactly one belongs to the builder."""
    def die(section):
        if section.id == "footer":
            raise RuntimeError("boom")

    run, _ = build_run(tmp_path, monkeypatch, RecordingBuilder(on_build=die))
    with pytest.raises(RuntimeError):
        drain(steps.step_build(run))

    second = RecordingBuilder()
    install_build(monkeypatch, second, blueprints=blueprints_for(*THREE))
    drain(steps.step_build(run))

    assert second.calls == ["footer"]
    assert all(s.status is BuildStatus.BUILT for s in read_bb(run).sections)


def test_reset_sends_one_section_back_and_the_rest_stay_built(tmp_path, monkeypatch):
    """"Just redo the hero" — the user-visible payoff of persisted state."""
    run, _ = build_run(tmp_path, monkeypatch)
    drain(steps.step_build(run))

    assert steps.reset_sections(run, ["hero"]) == ["hero"]
    by_id = {s.id: s for s in read_bb(run).sections}
    assert by_id["hero"].status is BuildStatus.PENDING
    assert by_id["nav"].status is BuildStatus.BUILT

    second = RecordingBuilder()
    install_build(monkeypatch, second, blueprints=blueprints_for(*THREE))
    drain(steps.step_build(run))
    assert second.calls == ["hero"]


def test_reset_refuses_a_section_that_does_not_exist(tmp_path, monkeypatch):
    """The negative. A typo that reports success and rebuilds nothing is the
    failure this guard is for."""
    run, _ = build_run(tmp_path, monkeypatch)
    drain(steps.step_build(run))

    with pytest.raises(ValueError, match="hero-section"):
        steps.reset_sections(run, ["hero-section"])
    assert all(s.status is BuildStatus.BUILT for s in read_bb(run).sections)


def test_a_built_section_whose_file_is_gone_is_rebuilt(tmp_path, monkeypatch):
    """The negative on the skip condition itself.

    Skipping on `status` alone resumes a workspace that was re-created from the
    scaffold into composing a page.tsx importing components that are not there —
    a build failure that says "module not found" and nothing about why.
    """
    run, _ = build_run(tmp_path, monkeypatch)
    drain(steps.step_build(run))
    (run.workspace / SECTIONS_DIR / "Hero.tsx").unlink()

    second = RecordingBuilder()
    install_build(monkeypatch, second, blueprints=blueprints_for(*THREE))
    drain(steps.step_build(run))

    assert second.calls == ["hero"], \
        "the status said built and the file was gone; the status won"
    assert {s.id: s.attempts for s in read_bb(run).sections}["hero"] == 2


# ------------------------------------------------------------- the decision log


def install_verify(monkeypatch, fixer, *, inspect=None, build=None):
    import sparrow.agents.builder as builder_mod
    import sparrow.blueprints as blueprints_mod
    import sparrow.cli as cli_mod

    monkeypatch.setattr(builder_mod, "Fixer", lambda: fixer)
    monkeypatch.setattr(blueprints_mod, "load_dir", lambda _d: {})
    monkeypatch.setattr(steps, "_inspect_once",
                        inspect or (lambda *_a, **_k: ([], {}, 0.0)))
    monkeypatch.setattr(cli_mod, "_run_build", build or (lambda _ws: (True, "ok")))


CLIPPED = Defect("high", "text-clipped", "the headline is clipped at 390px",
                 "hero @ 390px", "vision")
CLEAN = """export default function Hero() {
  return <section className="flex gap-8" />;
}
"""


def verify_run(tmp_path, monkeypatch, fixer, *, inspect):
    run = make_run(tmp_path, {"hero": CLEAN})
    # VERIFY only ever looks at sections it believes were built.
    steps._record_section(run, "hero", agent="builder", status=BuildStatus.BUILT,
                          bump_attempt=True)
    install_verify(monkeypatch, fixer, inspect=inspect)
    return run


def test_a_fixer_dispute_is_recorded_with_its_text(tmp_path, monkeypatch):
    """The one that cost real money. Four disputes burned three rounds and ~$2,
    and the text lived only in a dict that died with the process."""
    text = ("the headline is not clipped — it wraps to two lines at 390px, which "
            "is what the blueprint asks for")
    fixer = RecordingFixer(disputes={"hero": text})
    run = verify_run(tmp_path, monkeypatch, fixer,
                     inspect=lambda *_a, **_k: ([], {"hero": [CLIPPED]}, 0.0))
    drain(steps.step_verify(run))

    disputes = [d for d in read_bb(run).decisions if "DISPUTED" in d.summary]
    assert len(disputes) == 1, [d.summary for d in read_bb(run).decisions]
    assert disputes[0].agent == "fixer"
    assert "wraps to two lines" in disputes[0].summary, disputes[0].summary


def test_a_run_with_no_disputes_records_no_dispute(tmp_path, monkeypatch):
    """The negative. A log that says DISPUTED whatever happened is a log that
    cannot be used to find the run that disputed."""
    fixer = RecordingFixer(replies={"hero": CLEAN})
    calls = {"n": 0}

    def inspect(*_a, **_k):
        calls["n"] += 1
        return [], ({"hero": [CLIPPED]} if calls["n"] == 1 else {}), 0.0

    run = verify_run(tmp_path, monkeypatch, fixer, inspect=inspect)
    drain(steps.step_verify(run))

    bb = read_bb(run)
    assert [d for d in bb.decisions if "DISPUTED" in d.summary] == []
    assert [d for d in bb.decisions if "fix applied" in d.summary], \
        "the fix itself must still be recorded"


def test_a_fix_bumps_attempts_and_the_section_settles_clean(tmp_path, monkeypatch):
    fixer = RecordingFixer(replies={"hero": CLEAN})
    calls = {"n": 0}

    def inspect(*_a, **_k):
        calls["n"] += 1
        return [], ({"hero": [CLIPPED]} if calls["n"] == 1 else {}), 0.0

    run = verify_run(tmp_path, monkeypatch, fixer, inspect=inspect)
    drain(steps.step_verify(run))

    hero = read_bb(run).sections[0]
    assert hero.status is BuildStatus.BUILT
    assert hero.defects == []
    assert hero.attempts == 2, "one build plus one fix"


def test_a_section_still_defective_at_the_end_is_not_marked_built(tmp_path, monkeypatch):
    """The negative on the settle. Marking a section clean because the loop ran
    out of rounds is exactly the claim loop.py's fourth rule forbids."""
    fixer = RecordingFixer(replies={"hero": CLEAN})
    run = verify_run(tmp_path, monkeypatch, fixer,
                     inspect=lambda *_a, **_k: ([], {"hero": [CLIPPED]}, 0.0))
    drain(steps.step_verify(run))

    hero = read_bb(run).sections[0]
    assert hero.status is BuildStatus.DEFECTIVE
    assert hero.defects and "text-clipped" in hero.defects[0]


def test_defects_are_on_disk_before_the_fixer_is_ever_called(tmp_path, monkeypatch):
    """The fixer is the part that throws, times out, or gets killed. A defect
    list that only lands afterwards is absent exactly when it is needed."""
    seen: list = []

    class Watching(RecordingFixer):
        def fix(self, bb, section, code, defects):
            seen.append(read_bb(run).sections[0].model_copy())
            return super().fix(bb, section, code, defects)

    fixer = Watching(disputes={"hero": "not a real defect"})
    run = verify_run(tmp_path, monkeypatch, fixer,
                     inspect=lambda *_a, **_k: ([], {"hero": [CLIPPED]}, 0.0))
    drain(steps.step_verify(run))

    assert seen, "the fixer was never called"
    assert seen[0].status is BuildStatus.DEFECTIVE
    assert any("text-clipped" in d for d in seen[0].defects), seen[0].defects


def test_a_clean_verify_writes_no_defects_and_no_fix_decisions(tmp_path, monkeypatch):
    """The negative for the whole stage: nothing wrong, nothing recorded."""
    fixer = RecordingFixer()
    run = verify_run(tmp_path, monkeypatch, fixer,
                     inspect=lambda *_a, **_k: ([], {}, 0.0))
    before = read_bb(run).version
    drain(steps.step_verify(run))

    bb = read_bb(run)
    assert fixer.calls == []
    assert bb.sections[0].status is BuildStatus.BUILT and bb.sections[0].defects == []
    assert bb.version == before, \
        "a verify that found nothing must not churn the blackboard version"


def test_a_pending_section_is_not_settled_as_built(tmp_path, monkeypatch):
    """The negative on the settle's other edge. A section with no blueprint is
    never built and never inspected; the inspector having nothing to say about
    it is not evidence that it exists."""
    run = make_run(tmp_path, {"hero": CLEAN, "cta": CLEAN.replace("Hero", "Cta")})
    steps._record_section(run, "hero", agent="builder", status=BuildStatus.BUILT)
    install_verify(monkeypatch, RecordingFixer(),
                   inspect=lambda *_a, **_k: ([], {}, 0.0))
    drain(steps.step_verify(run))

    by_id = {s.id: s for s in read_bb(run).sections}
    assert by_id["hero"].status is BuildStatus.BUILT
    assert by_id["cta"].status is BuildStatus.PENDING, \
        "a section that was never built was marked built by the settle"


# --------------------------------------------------------- supersede at gate 2


def _directions(run, *signatures):
    (run.dir / "directions.json").write_text(json.dumps([
        {"index": i, "signature": sig,
         "design_system": {**DESIGN_SYSTEM.model_dump(mode="json"), "signature": sig}}
        for i, sig in enumerate(signatures)]))


def test_re_adopting_a_direction_names_the_one_it_replaces(tmp_path, monkeypatch):
    """CLAUDE.md §4: a replacement is not an addition, and the trace is what makes
    "why does this look different from what I approved" answerable."""
    run, _ = build_run(tmp_path, monkeypatch)
    monkeypatch.setattr(steps, "apply_design_system", lambda _r, _b: None)
    _directions(run, "a perforated remittance ribbon", "a stacked ledger rule")

    steps.adopt_direction(run, 0)
    steps.adopt_direction(run, 1)

    adopted = [d for d in read_bb(run).decisions if d.summary.startswith(steps._ADOPTED)]
    assert len(adopted) == 2
    assert adopted[0].supersedes is None, "the first direction replaced nothing"
    assert adopted[1].supersedes == adopted[0].id
    assert "stacked ledger rule" in adopted[1].summary
    assert read_bb(run).design_system.signature == "a stacked ledger rule"


def test_a_first_adoption_supersedes_nothing(tmp_path, monkeypatch):
    """The negative. A `supersedes` that is always populated points at whatever
    decision happened to be last and is worse than an empty field."""
    run, _ = build_run(tmp_path, monkeypatch)
    monkeypatch.setattr(steps, "apply_design_system", lambda _r, _b: None)
    _directions(run, "a perforated remittance ribbon")
    steps.adopt_direction(run, 0)

    adopted = [d for d in read_bb(run).decisions if d.summary.startswith(steps._ADOPTED)]
    assert [d.supersedes for d in adopted] == [None]


# ------------------------------------------------------------------ crash safety


def _store(tmp_path) -> Store:
    s = Store(tmp_path / "blackboard.json")
    s.init("t")
    return s


def test_a_crash_mid_write_leaves_the_previous_blackboard_intact(tmp_path, monkeypatch):
    """A half-written blackboard.json takes the whole project with it.

    The failure is injected at the rename, which is the last thing that happens
    and therefore the widest window: everything before it has already touched
    the filesystem.
    """
    store = _store(tmp_path)
    store.apply([{"op": "replace", "path": "/project_id", "value": "before"}],
                agent="t", summary="the state that must survive")
    before = store.path.read_text()

    def boom(self, _target):
        raise OSError("no space left on device")

    monkeypatch.setattr(Path, "replace", boom)
    with pytest.raises(OSError):
        store.apply([{"op": "replace", "path": "/project_id", "value": "after"}],
                    agent="t", summary="never lands")

    assert store.path.read_text() == before
    assert Blackboard.model_validate_json(store.path.read_text()).project_id == "before"
    assert list(tmp_path.glob("*.tmp")) == [], "scratch file left beside the blackboard"


def test_a_serialisation_failure_never_touches_the_file(tmp_path, monkeypatch):
    """The earlier window: the model does not serialise. Nothing may be truncated
    before that is known."""
    store = _store(tmp_path)
    before = store.path.read_text()
    monkeypatch.setattr(Blackboard, "model_dump_json",
                        lambda *_a, **_k: (_ for _ in ()).throw(TypeError("nope")))
    with pytest.raises(TypeError):
        store.apply([], agent="t", summary="never lands")

    assert store.path.read_text() == before


def test_the_write_actually_replaces_the_file_when_nothing_fails(tmp_path):
    """The negative for both tests above. A `_write` that never wrote anything
    would pass them and lose every run."""
    store = _store(tmp_path)
    before = store.path.read_text()
    r = store.apply([{"op": "replace", "path": "/project_id", "value": "after"}],
                    agent="t", summary="lands")

    assert isinstance(r, Applied)
    assert store.path.read_text() != before
    assert store.load().project_id == "after"


def test_two_writers_do_not_share_one_scratch_file(tmp_path, monkeypatch):
    """The temp name was `blackboard.tmp` for every writer of the project. Two
    processes interleaving into it rename halves of two blackboards into place,
    and the survivor parses as neither."""
    store = _store(tmp_path)
    names: list[str] = []
    real = Path.replace

    def watch(self, target):
        names.append(self.name)
        return real(self, target)

    monkeypatch.setattr(Path, "replace", watch)
    store.apply([], agent="t", summary="one")
    assert names and names[0] != "blackboard.tmp", names
    assert str(__import__("os").getpid()) in names[0], names


# ------------------------------------------------- the store is the only writer


def test_every_transition_leaves_a_decision_naming_its_agent(tmp_path, monkeypatch):
    """CLAUDE.md §3. The measured state was `decisions=0` on six finished builds,
    because the step functions wrote JSON directly and the only code that appends
    a Decision lives in `Store.apply`."""
    run, _ = build_run(tmp_path, monkeypatch)
    drain(steps.step_build(run))

    bb = read_bb(run)
    assert len(bb.decisions) == 3
    assert {d.agent for d in bb.decisions} == {"builder"}
    assert [d.id for d in bb.decisions] == ["d0001", "d0002", "d0003"]
    assert bb.version == 3
    # Every decision timestamped and ordered, so a run is replayable.
    assert [d.at for d in bb.decisions] == sorted(d.at for d in bb.decisions)


def test_a_no_op_record_does_not_append_a_decision(tmp_path, monkeypatch):
    """The negative. A writer that logs a decision per call rather than per
    transition fills the log with rounds in which nothing happened, which is the
    same as having no log."""
    run, _ = build_run(tmp_path, monkeypatch)
    drain(steps.step_build(run))
    before = read_bb(run)

    assert steps._record_section(run, "hero", agent="builder",
                                 status=BuildStatus.BUILT, defects=[]) is None
    after = read_bb(run)
    assert after.version == before.version
    assert len(after.decisions) == len(before.decisions)


def test_recording_an_unknown_section_is_rejected_not_raised(tmp_path, monkeypatch):
    """Persistence must never change what a run produces. A bookkeeping failure
    comes back as a reason the caller can report, never as a dead stage."""
    run, _ = build_run(tmp_path, monkeypatch)
    r = steps._record_section(run, "not-a-section", agent="builder",
                              status=BuildStatus.BUILT)
    assert isinstance(r, Rejected) and r.code == "unknown-section"
    assert read_bb(run).version == 0


def test_a_summary_is_one_line_and_bounded(tmp_path, monkeypatch):
    """Decisions are read back by agents, rendered into prompts and copied into
    logs. An unbounded model reply would make the decision log the largest field
    on the blackboard."""
    run, _ = build_run(tmp_path, monkeypatch)
    steps._note(run, agent="fixer", summary="x\ny\n" + "z" * 5000)
    d = read_bb(run).decisions[-1]

    assert "\n" not in d.summary
    assert len(d.summary) <= steps._SUMMARY_MAX
    assert d.summary.startswith("x y zzz")

"""The asset gate: the point at which the user's real material enters the run.

Before this gate existed, `curator` read each blueprint's asset briefs and
generated every one of them. `Provenance` had carried
`user_supplied | restyled | generated` from the beginning and only ever recorded
`generated` — which is what a missing gate looks like in the data. CLAUDE.md §2
names real content as the differentiator; a differentiator with no entry point
is not one.

Everything here is deterministic. The curator is stubbed, so no image is
generated and no transcription is bought; what is under test is the routing,
the validation, and what ends up recorded as provenance. The live exercise of
the real restyle + OCR fidelity gate is a separate, deliberate handful of calls.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from sparrow import steps
from sparrow.blackboard.schema import Blackboard, Prominence, Provenance
from sparrow.orchestrator import Stage

from conftest import drain, make_run

SECTION = 'export default function S() { return <section />; }\n'
UPLOADED = (200, 180, 120)
SCRUBBED = (10, 20, 30)


def blueprint(sid: str, assets: list[str]) -> str:
    listed = "\n".join(f"- {a}" for a in assets)
    return (f"# Blueprint: {sid}\n\n"
            f"Purpose: the {sid} section.\n\n"
            f"Slots: `headline`\n\n"
            + (f"Assets:\n{listed}\n\n" if assets else "")
            + "Structure: one column.\n")


def project(tmp_path, briefs: dict[str, list[str]]):
    run = make_run(tmp_path, {sid: SECTION for sid in briefs})
    for sid, assets in briefs.items():
        (run.dir / "blueprints" / f"{sid}.md").write_text(blueprint(sid, assets))
    return run


def png(colour=(20, 40, 30), size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------ the plan


def test_the_plan_carries_what_the_user_needs_to_answer(tmp_path):
    """§8: a gate is a concrete choice. "asset hero-1" is not answerable; the
    brief, the section it lands in and how big it will be are."""
    run = project(tmp_path, {"hero": ["A dashboard showing live control status"]})
    plan = steps.asset_plan(run)
    assert plan == [{
        "id": "hero-1", "section_id": "hero",
        "brief": "A dashboard showing live control status",
        "prominence": "dominant", "decision": None, "upload": None,
    }]


def test_prominence_says_how_large_the_upload_will_appear(tmp_path):
    run = project(tmp_path, {"hero": ["only image"],
                             "feature-grid": ["first", "second", "third"]})
    by_id = {a["id"]: a["prominence"] for a in steps.asset_plan(run)}
    assert by_id == {"hero-1": "dominant", "feature-grid-1": "supporting",
                     "feature-grid-2": "thumbnail", "feature-grid-3": "thumbnail"}


def test_chrome_is_never_offered(tmp_path):
    """A wordmark belongs to the client. The harness does not draw one, and it
    does not ask the user to choose between drawing one and skipping it."""
    run = project(tmp_path, {"nav": ["the company wordmark"],
                             "footer": ["the company wordmark"],
                             "hero": ["a product shot"]})
    assert [a["id"] for a in steps.asset_plan(run)] == ["hero-1"]


def test_a_run_whose_blueprints_ask_for_no_imagery_does_not_stop(tmp_path):
    run = project(tmp_path, {"hero": []})
    events, gate = drain(steps.step_asset_gate(run))
    assert gate is None, "an empty gate must not stop the run"
    assert "no blueprint asked for imagery" in events[-1].message


# ------------------------------------------------------------------ the gate


def test_the_gate_offers_three_choices_per_image(tmp_path):
    run = project(tmp_path, {"hero": ["a product shot"], "cta": ["a texture"]})
    _events, gate = drain(steps.step_asset_gate(run))

    assert gate.gate is Stage.GATE_ASSETS
    assert [o["asset_id"] for o in gate.options] == ["hero-1", "cta-1"]
    for option in gate.options:
        assert {c["choice"] for c in option["choices"]} == {"upload", "generate", "skip"}
        assert option["brief"] and option["section_id"] and option["prominence"]
    upload = gate.options[0]["choices"][0]
    assert upload["post_file_to"] == "/projects/t/assets/hero-1"


def test_every_image_must_be_decided_individually(tmp_path):
    run = project(tmp_path, {"hero": ["a"], "cta": ["b"]})
    drain(steps.step_asset_gate(run))

    with pytest.raises(ValueError, match="needs one of"):
        steps.record_asset_decisions(run, {"hero-1": "generate"})   # cta-1 unanswered


def test_a_meaningless_decision_is_refused(tmp_path):
    run = project(tmp_path, {"hero": ["a"]})
    drain(steps.step_asset_gate(run))
    with pytest.raises(ValueError, match="needs one of"):
        steps.record_asset_decisions(run, {"hero-1": "approve"})


def test_an_unknown_asset_is_refused(tmp_path):
    run = project(tmp_path, {"hero": ["a"]})
    drain(steps.step_asset_gate(run))
    with pytest.raises(ValueError, match="no such asset"):
        steps.record_asset_decisions(run, {"hero-1": "skip", "hero-9": "skip"})


def test_upload_without_a_file_is_refused_rather_than_quietly_generated(tmp_path):
    """A silent fallback to `generate` is how every site in this category ends up
    full of pictures nobody chose."""
    run = project(tmp_path, {"hero": ["a"]})
    drain(steps.step_asset_gate(run))
    with pytest.raises(ValueError, match="no file has been posted"):
        steps.record_asset_decisions(run, {"hero-1": "upload"})

    steps.record_upload(run, "hero-1", "shot.png", png())
    plan = steps.record_asset_decisions(run, {"hero-1": "upload"})
    assert plan[0]["decision"] == "upload" and plan[0]["upload"] == "hero-1.png"


def test_a_file_that_is_not_an_image_is_refused(tmp_path):
    run = project(tmp_path, {"hero": ["a"]})
    drain(steps.step_asset_gate(run))
    with pytest.raises(ValueError, match="not a readable image"):
        steps.record_upload(run, "hero-1", "notes.png", b"this is not a png")
    assert not list((run.dir / "uploads").glob("*")), "a rejected upload must not linger"


def test_an_upload_survives_the_plan_being_re_enumerated(tmp_path):
    """The gate can be reached twice — a crash between Halt and answer. A file
    posted before the crash must not be lost to the retry."""
    run = project(tmp_path, {"hero": ["a"]})
    drain(steps.step_asset_gate(run))
    steps.record_upload(run, "hero-1", "shot.png", png())

    _events, gate = drain(steps.step_asset_gate(run))
    assert gate is not None, "an unanswered gate must ask again"
    assert gate.options[0]["uploaded"] is True
    assert steps.load_plan(run)[0]["upload"] == "hero-1.png"


def test_an_answered_gate_does_not_ask_twice(tmp_path):
    run = project(tmp_path, {"hero": ["a"]})
    drain(steps.step_asset_gate(run))
    steps.record_asset_decisions(run, {"hero-1": "skip"})

    _events, gate = drain(steps.step_asset_gate(run))
    assert gate is None, "a decided gate must not re-ask on resume"
    assert steps.load_plan(run)[0]["decision"] == "skip"


# ------------------------------------------------------- executing the plan


class StubCurator:
    """Records what it was asked for. Returns real PNG bytes, because
    `derive_variants` is not stubbed — that part is deterministic and free."""

    def __init__(self, fidelity_ok: bool = True) -> None:
        StubCurator.last = self
        self.generated: list[str] = []
        self.restyled = 0
        self.checked = 0
        self.scrubs = 0
        self.saw: list[bytes] = []          # what each downstream call was handed
        self.fidelity_ok = fidelity_ok

    def generate(self, brief, _ds, **_kw):
        self.generated.append(brief)
        return png((90, 20, 20))

    def scrub(self, image):
        from sparrow.agents.curator import Scrub

        self.scrubs += 1
        self.saw.append(image)
        return Scrub(png(SCRUBBED), ["person name x1"], ["a scrubbed line"])

    def restyle(self, image, _ds, **_kw):
        self.restyled += 1
        self.saw.append(image)
        return png((10, 90, 40))

    def check_fidelity(self, before, _after):
        from sparrow.agents.curator import Fidelity

        self.checked += 1
        self.before = before
        return (Fidelity(ok=True, invented=[], lost=[]) if self.fidelity_ok
                else Fidelity(ok=False, invented=["visibility", "frameworks"], lost=[]))


def run_assets(run, monkeypatch, *, fidelity_ok=True):
    import sparrow.agents.curator as curator_mod

    monkeypatch.setattr(curator_mod, "Curator", lambda: StubCurator(fidelity_ok))
    events, _ = drain(steps.step_assets(run))
    bb = Blackboard.model_validate_json(run.blackboard_path.read_text())
    return events, bb, StubCurator.last


def decided(tmp_path, briefs, decisions, uploads=()):
    run = project(tmp_path, briefs)
    drain(steps.step_asset_gate(run))
    for aid in uploads:
        steps.record_upload(run, aid, "shot.png", png(UPLOADED))
    steps.record_asset_decisions(run, decisions)
    return run


def test_skip_records_no_asset_at_all(tmp_path, monkeypatch):
    """The builder then composes the section from type and layout — which is a
    better page than one carrying an invented picture of nothing."""
    run = decided(tmp_path, {"hero": ["a"]}, {"hero-1": "skip"})
    events, bb, cur = run_assets(run, monkeypatch)

    assert bb.assets == []
    assert cur.generated == [] and cur.restyled == 0
    assert "skipped" in events[0].message


def test_generate_is_still_available_and_marked_generated(tmp_path, monkeypatch):
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "generate"})
    _events, bb, cur = run_assets(run, monkeypatch)

    assert cur.generated == ["a dashboard"]
    assert cur.checked == 0, "generation invents its contents by construction — " \
                             "gating its text would gate the mechanism"
    assert [a.provenance for a in bb.assets] == [Provenance.GENERATED]
    assert bb.assets[0].prominence is Prominence.DOMINANT
    assert set(bb.assets[0].variants) == {"hero", "card", "mobile"}


def test_upload_is_restyled_and_marked_restyled_when_fidelity_holds(tmp_path, monkeypatch):
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "upload"},
                  uploads=["hero-1"])
    _events, bb, cur = run_assets(run, monkeypatch)

    assert cur.restyled == 1 and cur.checked == 1, \
        "the restyle path must run the fidelity gate — it is the one path that " \
        "can ship a claim the user never made"
    assert [a.provenance for a in bb.assets] == [Provenance.RESTYLED]
    assert bb.assets[0].rejected == []
    assert bb.assets[0].scrubbed == ["person name x1"], \
        "what the scrub replaced belongs on the asset, so the run stays auditable"


# ------------------------------------------------------------------ the scrub


def test_the_scrub_runs_before_anything_else_touches_the_upload(tmp_path, monkeypatch):
    """CLAUDE.md §7. `restyle` posts the file to a third-party image model and
    the result is published at the preview URL. A scrub after either is a scrub
    of a copy — the real customer data has already left."""
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "upload"},
                  uploads=["hero-1"])
    events, _bb, cur = run_assets(run, monkeypatch)

    assert cur.scrubs == 1
    assert cur.saw[0] != cur.saw[1], "the restyle must not be handed the upload"
    with Image.open(io.BytesIO(cur.saw[0])) as im:
        assert im.convert("RGB").getpixel((0, 0)) == UPLOADED   # scrub saw the real file
    with Image.open(io.BytesIO(cur.saw[1])) as im:
        assert im.convert("RGB").getpixel((0, 0)) == SCRUBBED   # restyle saw the scrub
    said = [e.message for e in events if "substituted" in e.message]
    assert said and "person name x1" in said[0], \
        "SS8 rules out a fourth gate, so the substitution is REPORTED instead"


def test_fidelity_is_measured_against_the_scrub_not_the_upload(tmp_path, monkeypatch):
    """Against the upload, every substitution the scrub made reads as a word the
    restyle invented, and every legitimate restyle of a dashboard is rejected.
    The image model's ground truth is what the image model was given."""
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "upload"},
                  uploads=["hero-1"])
    _events, _bb, cur = run_assets(run, monkeypatch)

    assert cur.before == ["a scrubbed line"], \
        "the scrub already read its own output back; buying that transcription " \
        "a second time is the only alternative"


def test_a_rejected_restyle_falls_back_to_the_scrub_not_the_upload(
        tmp_path, monkeypatch):
    """The restyle failing is no reason to publish the customer's data."""
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "upload"},
                  uploads=["hero-1"])
    _events, bb, _cur = run_assets(run, monkeypatch, fidelity_ok=False)

    assert bb.assets[0].provenance is Provenance.USER_SUPPLIED
    shipped = run.workspace / "public" / "assets" / "hero-1.png"
    with Image.open(shipped) as im:
        assert im.convert("RGB").getpixel((0, 0)) == SCRUBBED


def test_generation_is_not_scrubbed(tmp_path, monkeypatch):
    """Nothing generated is a picture of anybody's real customers."""
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "generate"})
    _events, bb, cur = run_assets(run, monkeypatch)
    assert cur.scrubs == 0 and bb.assets[0].scrubbed == []


def test_a_restyle_that_invents_words_falls_back_to_the_untouched_original(
        tmp_path, monkeypatch):
    """The negative, and the reason the gate exists. Measured in image-probe-02:
    asked to clean a capture whose copy was truncated by a chat widget, the model
    completed the sentences plausibly and entirely. Their real screenshot,
    unstyled, beats a beautiful one that says something untrue about their
    product."""
    run = decided(tmp_path, {"hero": ["a dashboard"]}, {"hero-1": "upload"},
                  uploads=["hero-1"])
    events, bb, cur = run_assets(run, monkeypatch, fidelity_ok=False)

    assert cur.restyled == 1 and cur.checked == 1
    assert [a.provenance for a in bb.assets] == [Provenance.USER_SUPPLIED]
    assert bb.assets[0].rejected and "invented" in bb.assets[0].rejected[0]
    blocked = [e for e in events if e.kind == "blocked"]
    assert blocked and "shipping your own screenshot instead" in blocked[0].message

    # The image that shipped is the user's, not the image model's.
    shipped = run.workspace / "public" / "assets" / "hero-1.png"
    with Image.open(shipped) as im:
        assert im.convert("RGB").getpixel((0, 0)) == SCRUBBED


def test_three_decisions_in_one_run(tmp_path, monkeypatch):
    run = decided(
        tmp_path,
        {"hero": ["a dashboard"], "feature-grid": ["one", "two"]},
        {"hero-1": "upload", "feature-grid-1": "generate", "feature-grid-2": "skip"},
        uploads=["hero-1"])
    events, bb, cur = run_assets(run, monkeypatch)

    assert {a.id: a.provenance.value for a in bb.assets} == {
        "hero-1": "restyled", "feature-grid-1": "generated"}
    assert cur.generated == ["one"], "a skipped image must not be generated anyway"
    assert "1 generated, 1 restyled · 1 skipped" in events[-1].message


def test_a_project_from_before_the_gate_still_generates(tmp_path, monkeypatch):
    """Resumability: an old project has no plan on disk and was never asked. It
    must behave exactly as it did before the gate existed, not stall."""
    run = project(tmp_path, {"hero": ["a dashboard"]})
    assert steps.load_plan(run) == []

    _events, bb, cur = run_assets(run, monkeypatch)
    assert cur.generated == ["a dashboard"]
    assert [a.provenance for a in bb.assets] == [Provenance.GENERATED]

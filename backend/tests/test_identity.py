"""The site's own identity: its name, and its mark.

Measured across all eight real projects before this existed:

    product_name        ""  on every single one
    nav brand mark      <PhoneCall /> from lucide, aria-label="Platform home"
    page <title>        "A platform for businesses to build voice AI agents q"
    hero screenshot     invents a company called "Off-Hook"

So the site was anonymous while the imagery generated FOR it invented brands of
its own — on one page, two of the four branded assets said `voiceowl` and two
said `Off-Hook`. The interviewer had asked for the name from the beginning and
correctly refuses to invent one; nothing followed up when it came back empty.

Everything here is deterministic: no model call, no image call, no browser, no
money. What is under test is where the name and the mark are ROUTED, and every
check has a negative twin — three deterministic checks in this repo were
confidently wrong until someone ran them against a case that should fail.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from sparrow import steps
from sparrow.agents.base import context_block
from sparrow.agents.curator import logo_placement
from sparrow.blackboard.schema import (Asset, AssetKind, Blackboard, Brief,
                                       Prominence, Provenance)
from sparrow.cli import _with_metadata
from sparrow.orchestrator import Stage

from conftest import (RecordingBuilder, blueprints_for, drain, install_build,
                      make_run, read_bb)

SECTION = 'export default function S() { return <section />; }\n'

SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 64">'
       b'<text x="0" y="48" fill="#111111">voiceowl</text></svg>')


def png(colour=(20, 20, 20), size=(240, 64), alpha=255) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, (*colour, alpha)).save(buf, "PNG")
    return buf.getvalue()


def project(tmp_path, section_ids=("nav", "hero", "footer"), pid="t"):
    run = make_run(tmp_path, {sid: SECTION for sid in section_ids}, pid=pid)
    for sid in section_ids:
        (run.dir / "blueprints" / f"{sid}.md").write_text(
            f"# Blueprint: {sid}\n\nPurpose: the {sid}.\n\nSlots: `headline`\n\n"
            + ("Assets:\n- a product capture\n\n" if sid == "hero" else "")
            + "Structure: one column.\n")
    return run


def set_name(run, name: str) -> None:
    bb = read_bb(run)
    bb.brief.product_name = name
    run.blackboard_path.write_text(bb.model_dump_json(indent=2))


# ----------------------------------------------------------------- gate 1

def test_gate_one_asks_for_the_name_when_the_interviewer_could_not_find_one(tmp_path):
    run = project(tmp_path)
    set_name(run, "")

    _events, gate = drain(steps.step_brief(run))
    assert gate is not None, "an unnamed run must not reach a generating stage"
    assert gate.gate is Stage.GATE_BRIEF, \
        "§8: asked at the gate that already exists, not at a fifth one"
    assert [o["kind"] for o in gate.options] == ["product_name"]
    assert gate.options[0]["choices"][0]["field"] == "product_name"


def test_gate_one_does_not_stop_a_run_that_already_has_a_name(tmp_path):
    """The negative. A gate that fires whether or not the answer is known is a
    gate that only ever hears "yes", which is what §8 actually rejects."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")

    events, gate = drain(steps.step_brief(run))
    assert gate is None
    assert "voiceowl.ai" in events[-1].message


def test_a_blank_answer_is_refused_rather_than_defaulted(tmp_path):
    run = project(tmp_path)
    set_name(run, "")
    for blank in ("", "   ", "\n\t "):
        with pytest.raises(ValueError, match="cannot be blank"):
            steps.record_product_name(run, blank)
    assert read_bb(run).brief.product_name == ""


def test_the_answer_lands_on_the_blackboard_and_clears_the_gate(tmp_path):
    run = project(tmp_path)
    set_name(run, "")
    assert steps.record_product_name(run, "  voiceowl.ai  ") == "voiceowl.ai"

    bb = read_bb(run)
    assert bb.brief.product_name == "voiceowl.ai"
    assert any("voiceowl.ai" in d.summary for d in bb.decisions), \
        "§3: the transition is recorded, so the run stays replayable"
    _events, gate = drain(steps.step_brief(run))
    assert gate is None


# ------------------------------------------------- place 1: the copy's prompt

def test_the_name_is_injected_into_every_agent_prompt(tmp_path):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    block = context_block(read_bb(run))
    assert "PRODUCT NAME: voiceowl.ai" in block
    assert "not given" not in block, \
        "the 'not given' branch is what all eight measured projects took"


def test_an_unnamed_brief_takes_the_refuse_to_invent_branch(tmp_path):
    """The negative. A project from before gate 1 must still not let an agent
    make a name up — it refers to the product generically instead."""
    run = project(tmp_path)
    set_name(run, "")
    block = context_block(read_bb(run))
    assert "PRODUCT NAME: not given" in block and "do NOT invent one" in block


def test_the_copy_agent_is_told_the_name(tmp_path):
    """`content_editor` builds its own brief block rather than using
    `context_block`, so the name reaching one proves nothing about the other."""
    from sparrow.agents.content_editor import ContentEditor
    from sparrow.blackboard.schema import Blueprint

    seen = {}

    class FakeProvider:
        name = "fake"
        _agent_name = ""

    editor = ContentEditor(provider=FakeProvider())
    def capture(*, system, user, images=None):
        seen["user"] = user
        raise LookupError("stop here — the prompt is what is under test")
    editor.call = capture

    brief = Brief(product_name="voiceowl.ai", category="c", offering="o",
                  audience="a", tone="t", primary_action="p")
    with pytest.raises(LookupError):
        editor.write(brief, [], Blueprint(id="hero", purpose="p", slots=["headline"],
                                          structure="s"), section_id="hero")
    assert "voiceowl.ai" in seen["user"]


# ------------------------------------------------ place 2: the browser tab

def test_the_name_leads_the_page_title_and_description(tmp_path):
    src = 'export const metadata: Metadata = {\n  title: "",\n  description: "",\n};\n'
    brief = Brief(product_name="voiceowl.ai", category="c",
                  offering="A platform for businesses to build voice AI agents "
                           "quickly. It supports complex workflows.",
                  audience="a", tone="t", primary_action="p")
    out = _with_metadata(src, brief)

    assert 'title: "voiceowl.ai — ' in out
    assert 'description: "voiceowl.ai — ' in out
    title = out.split('title: "')[1].split('"')[0]
    assert len(title) <= 60 and not title.endswith(("q", "-")), \
        "the old slice cut mid-word: 'build voice AI agents q'"


def test_the_title_is_rewritten_on_a_layout_that_already_has_one(tmp_path):
    """The negative for the guard. The old version only fired while the field
    was still `""`, so a name settled after the first compose — which is now the
    normal case, since gate 1 asks for it — could never reach the tab."""
    src = 'export const metadata: Metadata = {\n  title: "A platform for busine",\n  description: "old",\n};\n'
    brief = Brief(product_name="voiceowl.ai", category="c", offering="A platform.",
                  audience="a", tone="t", primary_action="p")
    assert 'title: "voiceowl.ai — A platform"' in _with_metadata(src, brief)


def test_an_unnamed_brief_still_gets_a_title(tmp_path):
    """Projects created before gate 1 asked. They must degrade, not crash."""
    src = 'export const metadata: Metadata = {\n  title: "",\n  description: "",\n};\n'
    brief = Brief(product_name="", category="c", offering="A platform for teams.",
                  audience="a", tone="t", primary_action="p")
    out = _with_metadata(src, brief)
    assert 'title: "A platform for teams"' in out and "—" not in out


# ------------------------------------------ place 3: the nav and the footer

def test_only_chrome_is_told_to_draw_the_brand(tmp_path):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    bb = read_bb(run)
    by_id = {s.id: s for s in bb.sections}

    for chrome in ("nav", "footer"):
        block = steps.identity_block(run, bb, by_id[chrome])
        assert "voiceowl.ai" in block and "BRAND ENTRY POINT" in block

    assert steps.identity_block(run, bb, by_id["hero"]) == "", \
        "a content section carrying this would draw a wordmark of its own"


def test_the_wordmark_instruction_names_the_failure_it_replaces(tmp_path):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    bb = read_bb(run)
    nav = next(s for s in bb.sections if s.id == "nav")
    block = steps.identity_block(run, bb, nav)
    # The measured failure was a lucide glyph plus an aria-label. Both are named
    # so the instruction rules out the thing that actually happened.
    assert "lucide" in block and "aria-label" in block


def test_step_build_hands_the_identity_to_the_builder(tmp_path, monkeypatch):
    """Computed in the step and consumed in the agent — the seam where this
    repo keeps finding values that were derived and then dropped."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    builder = RecordingBuilder()
    install_build(monkeypatch, builder,
                  blueprints=blueprints_for("nav", "hero", "footer"))
    drain(steps.step_build(run))

    assert "voiceowl.ai" in builder.kwargs["nav"]["identity"]
    assert "voiceowl.ai" in builder.kwargs["footer"]["identity"]
    assert builder.kwargs["hero"]["identity"] == ""


def test_an_unnamed_project_still_builds(tmp_path, monkeypatch):
    """The negative. Projects predate the gate; a step that raised on a blank
    name would make every one of them unresumable."""
    run = project(tmp_path)
    set_name(run, "")
    builder = RecordingBuilder()
    install_build(monkeypatch, builder,
                  blueprints=blueprints_for("nav", "hero", "footer"))
    drain(steps.step_build(run))

    assert builder.kwargs["nav"]["identity"] == ""
    assert sorted(builder.calls) == ["footer", "hero", "nav"]


# ---------------------------------------------------------------- the logo

def add_logo(run, *, suffix=".png", data=None) -> Asset:
    bb = read_bb(run)
    path = run.workspace / "public" / "assets" / f"nav-logo{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if data is not None else png())
    logo = Asset(id="nav-logo", section_id="nav", kind=AssetKind.LOGO,
                 brief="the mark", prominence=Prominence.THUMBNAIL,
                 provenance=Provenance.USER_SUPPLIED,
                 path=f"assets/{path.name}", width=240, height=64)
    bb.assets = [logo]
    run.blackboard_path.write_text(bb.model_dump_json(indent=2))
    return logo


def test_the_logo_never_reaches_the_builder_as_a_section_image(tmp_path, monkeypatch):
    """The <assets> block carries "a dominant asset is at least 60% of the
    section's height". That rule firing on a nav asset is what produced the
    full-width blank box above the hero."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    add_logo(run)
    builder = RecordingBuilder()
    install_build(monkeypatch, builder,
                  blueprints=blueprints_for("nav", "hero", "footer"))
    drain(steps.step_build(run))

    assert builder.kwargs["nav"]["assets"] == [], \
        "the logo goes through `identity`, never through the prominence machinery"
    assert "nav-logo" in builder.kwargs["nav"]["identity"]
    assert "nav-logo" in builder.kwargs["footer"]["identity"], \
        "one mark, both pieces of chrome — it is site identity, not a nav image"


def test_the_identity_block_forbids_redrawing_in_the_words_that_matter(tmp_path):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    add_logo(run)
    bb = read_bb(run)
    nav = next(s for s in bb.sections if s.id == "nav")
    block = steps.identity_block(run, bb, nav)

    assert "RECOLOURED, NEVER REDRAWN" in block
    for banned in ("trace it", "re-letter", "stretch"):
        assert banned in block


def test_with_no_logo_the_name_itself_is_the_mark(tmp_path):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    bb = read_bb(run)
    nav = next(s for s in bb.sections if s.id == "nav")
    block = steps.identity_block(run, bb, nav)

    assert "no logo file" in block
    assert "icon as a stand-in" in block


# --------------------------------------------------- executing a logo choice

from test_asset_gate import run_assets  # noqa: E402  — the same stub curator


def logo_run(tmp_path, decision, *, upload=None):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    if upload is not None:
        steps.record_upload(run, "nav-logo", upload[0], upload[1])
    steps.record_asset_decisions(run, {"nav-logo": decision, "hero-1": "skip"})
    return run


def test_an_uploaded_logo_is_never_restyled_and_never_scrubbed(tmp_path, monkeypatch):
    """The hard rule, asserted at the only place it can be broken.

    An image model asked to restyle a mark redraws the letterforms. On a
    dashboard that is an invented label the fidelity gate catches; on a
    trademark it is somebody's registered mark come back subtly wrong. The scrub
    is skipped for a different reason: it substitutes person and org names, and
    a founder's name IS the mark on a great many logos.
    """
    run = logo_run(tmp_path, "upload", upload=("logo.png", png()))
    _events, bb, cur = run_assets(run, monkeypatch)

    assert cur.restyled == 0, "a logo must never reach Curator.restyle"
    assert cur.scrubs == 0 and cur.checked == 0
    assert cur.generated == []
    logo = bb.logo()
    assert logo is not None
    assert logo.kind is AssetKind.LOGO
    assert logo.provenance is Provenance.USER_SUPPLIED
    assert logo.variants == {}, "centre-cropping a wordmark to 800x800 is nonsense"
    assert (run.workspace / "public" / logo.path).read_bytes() == png(), \
        "byte-identical: the file is copied through, not processed"


def test_an_uploaded_content_image_still_is_restyled(tmp_path, monkeypatch):
    """The negative twin. If the logo exemption were written too widely — say,
    on the section rather than on the kind — it would silently switch off the
    restyle and the fidelity gate for ordinary uploads too."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_upload(run, "hero-1", "shot.png", png((200, 180, 120)))
    steps.record_asset_decisions(run, {"nav-logo": "wordmark", "hero-1": "upload"})
    _events, _bb, cur = run_assets(run, monkeypatch)

    assert cur.scrubs == 1 and cur.restyled == 1 and cur.checked == 1


def test_wordmark_produces_no_file_and_no_asset(tmp_path, monkeypatch):
    run = logo_run(tmp_path, "wordmark")
    events, bb, cur = run_assets(run, monkeypatch)

    assert bb.logo() is None and bb.assets == []
    assert cur.generated == [] and cur.restyled == 0, \
        "there is no generate path for a logo, so wordmark cannot fall into one"
    assert any("wordmark" in e.message for e in events)


def test_an_svg_logo_is_accepted_and_a_svg_content_image_is_not(tmp_path):
    """SVG is the format the hard rule actually wants — `currentColor` recolours
    a mark with no pixel touched. It is refused for a content image because
    everything downstream of one (scrub, restyle, variants) is raster work, and
    it would fail there instead: minutes later, one gate on."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))

    entry = steps.record_upload(run, "nav-logo", "logo.png", SVG)
    assert entry["upload"] == "nav-logo.svg", "sniffed from the bytes, not the name"

    with pytest.raises(ValueError, match="accepted for your logo"):
        steps.record_upload(run, "hero-1", "shot.svg", SVG)


def test_a_broken_svg_is_refused(tmp_path):
    run = project(tmp_path)
    drain(steps.step_asset_gate(run))
    with pytest.raises(ValueError, match="not readable SVG"):
        steps.record_upload(run, "nav-logo", "logo.svg", b"<svg><text>oops")


# ------------------------------- place 4: the curator's briefs and the logo

def test_the_name_and_the_mark_both_reach_the_generator(tmp_path, monkeypatch):
    """This is the one that fixes "Off-Hook". A generated product surface shows
    branding whether or not the brief mentions any; with nothing given it makes
    one up, differently per call."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_upload(run, "nav-logo", "logo.png", png())
    steps.record_asset_decisions(run, {"nav-logo": "upload", "hero-1": "generate"})
    _events, _bb, cur = run_assets(run, monkeypatch)

    assert cur.gen_kwargs == [{"product_name": "voiceowl.ai", "logo": png()}], \
        "the mark itself, not merely a note that one exists"


def test_generation_without_a_logo_still_carries_the_name(tmp_path, monkeypatch):
    """The negative. Most projects choose `wordmark`; the name must reach the
    generator anyway, because the name alone is what stops "Off-Hook"."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_asset_decisions(run, {"nav-logo": "wordmark", "hero-1": "generate"})
    _events, _bb, cur = run_assets(run, monkeypatch)

    assert cur.gen_kwargs == [{"product_name": "voiceowl.ai", "logo": None}]


def test_a_generated_image_that_shows_the_wrong_brand_is_recorded(tmp_path, monkeypatch):
    """Prompting is not proof. The check reads the image back and the failure is
    recorded rather than papered over — there is no untouched original to fall
    back to, so the honest answer is to say so."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_asset_decisions(run, {"nav-logo": "wordmark", "hero-1": "generate"})
    events, bb, cur = run_assets(run, monkeypatch, branding_ok=False)

    assert cur.branded == 1
    asset = next(a for a in bb.assets if a.id == "hero-1")
    assert asset.rejected and "branding not confirmed" in asset.rejected[0]
    assert any(e.kind == "blocked" and "does not show your name" in e.message
               for e in events)


def test_a_correctly_branded_image_records_nothing(tmp_path, monkeypatch):
    """The negative twin: a check that fires on everything has not checked."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_asset_decisions(run, {"nav-logo": "wordmark", "hero-1": "generate"})
    events, bb, cur = run_assets(run, monkeypatch, branding_ok=True)

    assert cur.branded == 1
    assert next(a for a in bb.assets if a.id == "hero-1").rejected == []
    assert not [e for e in events if e.kind == "blocked"]


def test_the_branding_check_matches_the_name_however_it_is_typeset():
    """Real assertion on the real matcher — the stub above proves the routing,
    this proves the rule. A mark rendered "Voice Owl" is the right company."""
    from sparrow.agents.curator import Curator

    class Reader(Curator):
        def __init__(self, lines):
            self.lines = lines

        def transcribe(self, _image):
            return self.lines

    for typeset in (["voiceowl"], ["VOICEOWL"], ["Voice Owl"], ["voiceowl.ai"],
                    ["Dashboard", "voice-owl", "Live"]):
        assert Reader(typeset).check_branding(b"", "voiceowl.ai").ok, typeset

    # The measured failure, and the two ways a near-miss must still fail.
    for wrong in (["Off-Hook", "Overview", "WORK"], ["Owl Voice"], ["Dashboard"]):
        result = Reader(wrong).check_branding(b"", "voiceowl.ai")
        assert not result.ok, wrong
        assert "voiceowl" in result.reason()

    assert Reader(["anything"]).check_branding(b"", "").ok, \
        "an unnamed project has nothing to check against"


# ------------------------------------------------ deterministic logo placement

def test_placement_is_measured_and_every_branch_preserves_the_drawing(tmp_path):
    from sparrow.fixtures.ledgerline import DESIGN_SYSTEM

    d = tmp_path / "logos"
    d.mkdir()

    svg = d / "mark.svg"
    svg.write_bytes(SVG)
    assert "currentColor" in logo_placement(svg, DESIGN_SYSTEM)

    dark_on_transparent = d / "dark.png"
    dark_on_transparent.write_bytes(png((17, 17, 17), alpha=255))
    said = logo_placement(dark_on_transparent, DESIGN_SYSTEM)
    assert "contrast" in said and ":1" in said, "the number is quoted, not the verdict"

    # A mark whose ink matches the page ground: it cannot be seen, and the fix
    # is a knockout or a chip — never a redraw.
    ground = {c.token: c for c in DESIGN_SYSTEM.colors}["background"].value
    from sparrow.palette import parse
    grey = round((parse(ground)[0] ** 3) ** (1 / 2.2) * 255)
    invisible = d / "invisible.png"
    invisible.write_bytes(png((grey, grey, grey), alpha=200))
    said = logo_placement(invisible, DESIGN_SYSTEM)
    assert "mask-image" in said or "chip" in said
    assert "redraw" in said or "exactly as it is" in said

    empty = d / "empty.png"
    empty.write_bytes(png((0, 0, 0), alpha=0))
    assert "fully transparent" in logo_placement(empty, DESIGN_SYSTEM)


ALTERING = ("redraw", "trace", "re-letter", "rebuild", "key out", "substitute")


def test_no_placement_branch_ever_permits_altering_the_mark(tmp_path):
    """The negative sweep: whatever the measurement says, none of the branches
    may come out as permission to change the drawing.

    Checked by looking at what PRECEDES each verb rather than at whether the
    verb is present — the instructions have to name these actions in order to
    forbid them, so a test that simply banned the words would force the rule to
    stop saying what it rules out.
    """
    import re

    from sparrow.fixtures.ledgerline import DESIGN_SYSTEM

    d = tmp_path / "logos"
    d.mkdir()
    cases = {"a.svg": SVG,
             "b.png": png((17, 17, 17), alpha=255),
             "c.png": png((250, 250, 250), alpha=255),
             "d.png": png((120, 120, 120), alpha=120)}
    for name, data in cases.items():
        path = d / name
        path.write_bytes(data)
        said = " ".join(logo_placement(path, DESIGN_SYSTEM).lower().split())
        for verb in ALTERING:
            for m in re.finditer(re.escape(verb), said):
                before = said[max(0, m.start() - 24):m.start()]
                assert ("do not" in before or "never" in before
                        or "would destroy" in before), \
                    f"{name}: {verb!r} appears unprohibited — ...{before}{verb}..."


def test_the_sweep_would_catch_a_branch_that_did_permit_it(tmp_path):
    """The negative twin of the negative sweep. The check above passes trivially
    if it never actually looks, so prove it fails on text that permits."""
    import re

    said = "recolour it, or trace it in a webfont if that is easier"
    hits = [m for verb in ALTERING for m in re.finditer(re.escape(verb), said)
            if "do not" not in said[max(0, m.start() - 24):m.start()]
            and "never" not in said[max(0, m.start() - 24):m.start()]]
    assert hits, "the sweep must actually flag a permission when one is present"


# -------------------------------------------------------------- resume

def test_an_asset_already_produced_is_not_paid_for_twice(tmp_path, monkeypatch):
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_asset_decisions(run, {"nav-logo": "wordmark", "hero-1": "generate"})
    _events, bb, cur = run_assets(run, monkeypatch)
    assert cur.generated == ["a product capture"]

    events, bb2, cur2 = run_assets(run, monkeypatch)
    assert cur2.generated == [], "a second pass must not re-buy what is on disk"
    assert [a.id for a in bb2.assets] == [a.id for a in bb.assets]
    assert any("already produced" in e.message for e in events)


def test_reset_makes_it_payable_again_and_removes_the_file(tmp_path, monkeypatch):
    """The negative twin, and the reason `reset_assets` exists: uploading a logo
    means every surface generated before it carries invented branding."""
    run = project(tmp_path)
    set_name(run, "voiceowl.ai")
    drain(steps.step_asset_gate(run))
    steps.record_asset_decisions(run, {"nav-logo": "wordmark", "hero-1": "generate"})
    run_assets(run, monkeypatch)
    on_disk = run.workspace / "public" / "assets" / "hero-1.png"
    assert on_disk.exists()

    assert steps.reset_assets(run, ["hero-1"]) == ["hero-1"]
    assert not on_disk.exists(), "a record without a file resumes into a 404"
    assert read_bb(run).assets == []

    _events, _bb, cur = run_assets(run, monkeypatch)
    assert cur.generated == ["a product capture"]


def test_resetting_an_unknown_asset_is_refused(tmp_path):
    run = project(tmp_path)
    with pytest.raises(ValueError, match="no such asset"):
        steps.reset_assets(run, ["nope"])

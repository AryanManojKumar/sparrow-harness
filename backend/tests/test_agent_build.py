"""The agent-designed build (B+): Sparrow's material in, Sparrow's guardrails out.

The agent and the workshop are replaced by a recorder, so what is tested is
everything Sparrow itself decides: what the agent is handed, when the site
counts as handed over, which findings go back as a fix turn, that the fix loop
caps, and that the run always ends at the preview gate.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import pytest

from sparrow import agent_build, brand, dossier, gateway, guard
from sparrow.blackboard.schema import Asset, AssetKind, Blackboard, Provenance
from sparrow.fixtures.ledgerline import BRIEF, CONSTRAINTS, DESIGN_SYSTEM
from sparrow.orchestrator import Halt, Run, Stage


# ── claims ──────────────────────────────────────────────────────────────────

def test_display_type_and_ordinals_are_not_claims():
    code = '<h2>ENTER THE FIELD</h2><span>01</span><p>Find your squad. Land together.</p>'
    assert guard.claims_in(code, set()) == []


def test_names_and_figures_are_claims_even_in_capitals():
    code = '<p>Available on Steam and Xbox</p><h3>RUNS AT 120 FPS</h3>'
    assert guard.claims_in(code, set()) == ["120", "Steam", "Xbox"]


def test_confirmed_words_pass():
    assert guard.claims_in("<p>Built for Acme teams</p>", {"acme"}) == []


def test_assets_missing_and_unused_count_any_crop(tmp_path):
    (tmp_path / "public/assets").mkdir(parents=True)
    (tmp_path / "public/assets/hero-1.png").write_bytes(b"x")
    (tmp_path / "public/assets/hero-1--card.webp").write_bytes(b"x")
    (tmp_path / "src/app").mkdir(parents=True)
    (tmp_path / "src/app/page.tsx").write_text(
        '<img src="/p/assets/hero-1--card.webp"/><img src="/p/assets/ghost.png"/>')
    found = guard.check_assets(tmp_path, ["hero-1.png", "cta-3.png"])
    kinds = {f.kind: f.detail for f in found}
    assert "ghost.png" in kinds["missing-asset"]
    assert "cta-3.png" in kinds["unused-asset"] and "hero-1" not in kinds["unused-asset"]


# ── brand ───────────────────────────────────────────────────────────────────

def _png(rgb) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), rgb).save(buf, "PNG")
    return buf.getvalue()


def test_a_reference_red_on_the_page_is_flagged_and_a_different_hue_is_not():
    pal = {"playvalorant.com": {"surfaces": [{"hex": "#1a242e"}], "accent": "#1a242e",
                                "brand": ["#ff4655"]}}
    hits = brand.too_close([_png((255, 70, 85))], pal)
    assert hits and hits[0]["site"] == "playvalorant.com" and hits[0]["delta_e"] < 15
    assert brand.too_close([_png((212, 238, 69))], pal) == []


def test_reference_colours_keep_old_palettes_working():
    assert brand.reference_colours({"surfaces": [{"hex": "#ff9b01"}], "accent": None}) == ["#ff9b01"]


# ── gateway usage ───────────────────────────────────────────────────────────

def test_usage_is_read_from_the_stream_tail_and_summed_per_project(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway, "USAGE_LOG", tmp_path / "u.jsonl")
    tail = (b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
            b'data: {"choices":[],"usage":{"prompt_tokens":1000,"completion_tokens":100,'
            b'"prompt_tokens_details":{"cached_tokens":800}}}\n\ndata: [DONE]\n\n')
    u = gateway.usage_in_stream(tail)
    assert u["prompt_tokens"] == 1000
    gateway.record_usage("site-a", "m", u)
    gateway.record_usage("site-b", "m", u)
    tot = gateway.usage_since("site-a", 0)
    assert tot["calls"] == 1 and tot["cached"] == 800 and tot["cost"] > 0


# ── dossier ─────────────────────────────────────────────────────────────────

def _bb() -> Blackboard:
    return Blackboard(project_id="ledger", brief=BRIEF, constraints=CONSTRAINTS,
                      design_system=DESIGN_SYSTEM, assets=[Asset(
                          id="hero-1", section_id="hero", kind=AssetKind.IMAGE,
                          brief="the close dashboard", provenance=Provenance.GENERATED,
                          path="assets/hero-1.png")])


def test_agent_dossier_has_material_and_rules_but_no_token_table():
    text = dossier.render(_bb(), {}, "/projects/ledger/preview", references=["https://a.com"])
    assert "Design system" not in text and "| token |" not in text
    assert "refs/" in text and "https://a.com (the main one)" in text
    assert "`/projects/ledger/preview/assets/hero-1.png`" in text
    for c in CONSTRAINTS:
        assert f'"{c.text}"' in text
    assert "## Build rules" in text


# ── the stages ──────────────────────────────────────────────────────────────

class FakeWorkshop:
    """Records what the office sent; plays back scripted turn endings."""

    url = "http://workshop"
    turns: list[str] = []
    endings: list[dict] = []
    links_found: list[list[dict]] = []
    looks: list[bool] = []
    fresh: list[bool] = []

    def __init__(self, *a, **k) -> None:
        pass

    def push(self, pid, workspace):
        FakeWorkshop.pushed = workspace

    def put_dossier(self, pid, text):
        FakeWorkshop.dossier = text

    def put_asset(self, pid, name, data, replace=False):
        FakeWorkshop.assets_put.append((name, replace))
        return {"path": f"public/assets/{name}"}

    def turn(self, pid, message, token, look=True, fresh=False, look_only=False):
        FakeWorkshop.looks.append("only" if look_only else look)
        FakeWorkshop.fresh.append(fresh)
        FakeWorkshop.turns.append(message)
        yield {"kind": "tool", "tool": "write", "target": "src/app/page.tsx", "detail": "9 lines"}
        yield FakeWorkshop.endings.pop(0)

    def pull(self, pid):
        import tarfile
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            data = b"<motion.h1 whileInView={{opacity: 1}}>Close the books</motion.h1>"
            info = tarfile.TarInfo("src/app/page.tsx")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        return buf.getvalue()

    def links(self, pid):
        return FakeWorkshop.links_found.pop(0) if FakeWorkshop.links_found else []

    page: dict = {}

    def measure(self, pid, route="/"):
        return FakeWorkshop.page

    def shots(self, pid, route="/"):
        return [{"data": base64.b64encode(_png((240, 240, 240))).decode()}]


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("GATEWAY_SECRET", "s" * 40)
    monkeypatch.setattr(gateway, "USAGE_LOG", tmp_path / "u.jsonl")
    import sparrow.workshop.client as client
    monkeypatch.setattr(client, "Workshop", FakeWorkshop)
    FakeWorkshop.turns, FakeWorkshop.endings, FakeWorkshop.links_found = [], [], []
    FakeWorkshop.looks, FakeWorkshop.fresh, FakeWorkshop.assets_put = [], [], []
    FakeWorkshop.page = {}
    run = Run("ledger", tmp_path, {})
    run.dir.mkdir(parents=True)
    run.blackboard_path.write_text(_bb().model_dump_json())
    (run.workspace / "src").mkdir(parents=True)
    (run.workspace / "package.json").write_text("{}")
    (run.dir / "sources").mkdir()
    (run.dir / "sources/a_com-b00.png").write_bytes(b"png")
    (run.dir / "sources/a_com-v00.png").write_bytes(b"png")
    (run.dir / "urls.json").write_text(json.dumps(["https://b.com", "https://a.com"]))
    (run.dir / "sources/primary.txt").write_text("a.com")
    return run


def test_build_hands_over_material_and_marks_the_studio_only_on_success(project):
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": "abc", "reverted": False,
                             "reply": "Built it.", "changed": ["src/app/page.tsx"]}]
    events = list(agent_build.step_build(project))
    assert [p.name for p in (project.workspace / "refs").iterdir()] == ["a_com-b00.png"]
    assert FakeWorkshop.turns[0].startswith("Build a complete marketing website for")
    assert "https://a.com (the main reference)" in FakeWorkshop.turns[0]
    assert "The direction the owner chose" in FakeWorkshop.dossier
    assert (project.dir / "studio.json").is_file()
    assert events[-1].kind == "done"


def test_a_build_that_never_lands_leaves_the_pipeline_in_charge(project):
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": None, "reverted": True}]
    with pytest.raises(RuntimeError):
        list(agent_build.step_build(project))
    assert not (project.dir / "studio.json").exists()
    assert agent_build.agent_designed(project.dir)


# ── images made while the agent builds ──────────────────────────────────────

PLAN = [
    {"id": "nav-logo", "section_id": "nav", "kind": "logo", "brief": "the mark",
     "prominence": "supporting", "decision": "upload", "upload": "logo.png"},
    {"id": "hero-1", "section_id": "hero", "kind": "image", "brief": "the dashboard",
     "prominence": "dominant", "decision": "generate"},
    {"id": "grid-1", "section_id": "grid", "kind": "image", "brief": "a detail",
     "prominence": "supporting", "decision": "generate"},
    {"id": "quote-1", "section_id": "quote", "kind": "image", "brief": "a face",
     "prominence": "supporting", "decision": "skip"},
]


@pytest.fixture
def planned(project, monkeypatch):
    from PIL import Image
    from sparrow import steps

    monkeypatch.setattr(steps, "resolved_plan", lambda run: [dict(a) for a in PLAN])
    (project.dir / "uploads").mkdir()
    Image.new("RGB", (300, 100), (10, 20, 30)).save(project.dir / "uploads/logo.png")
    return project


def _made(run, ids):
    """A stand-in ASSETS stage: real (noisy) files for `ids`, recorded as made."""
    from PIL import Image
    from sparrow import steps
    from sparrow.agents.curator import derive_variants

    def fake(r):
        bb = steps._bb(r)
        for a in bb.assets:
            if a.id in ids:
                f = r.workspace / "public" / a.path
                Image.effect_noise((1536, 1024), 60).convert("RGB").save(f)
                derive_variants(f)
                a.provenance = Provenance.GENERATED
        yield from ()
        bb.assets = [a for a in bb.assets if a.id in ids or a.kind == AssetKind.LOGO]
        steps._replace(r, "/assets", [a.model_dump(mode="json") for a in bb.assets],
                       agent="curator", summary="made")
        (r.dir / steps.PENDING_ASSETS).unlink(missing_ok=True)
    return fake


def test_stand_ins_have_the_final_paths_and_sizes_and_the_logo_is_real(planned):
    from PIL import Image
    from sparrow import steps

    stand_ins = agent_build.placeholders(planned, steps._bb(planned))
    assert stand_ins == ["hero-1", "grid-1"]
    assert steps.pending_assets(planned) == {"hero-1", "grid-1"}
    public = planned.workspace / "public" / "assets"
    with Image.open(public / "hero-1.png") as im:
        assert im.size == (1536, 1024)
    assert (public / "hero-1--card.png").is_file()
    assert (public / "nav-logo.png").read_bytes() == (planned.dir / "uploads/logo.png").read_bytes()
    assert not (public / "quote-1.png").exists()
    ids = [a.id for a in steps._bb(planned).assets]
    assert ids == ["nav-logo", "hero-1", "grid-1"]


def test_build_starts_on_stand_ins_then_looks_once_the_images_are_in(planned, monkeypatch):
    from sparrow import steps

    monkeypatch.setattr(steps, "step_assets", _made(planned, {"hero-1"}))
    list(agent_build.step_assets(planned))
    FakeWorkshop.endings = [
        {"kind": "done", "checkpoint": "abc", "reverted": False, "reply": "Built."},
        {"kind": "done", "checkpoint": "def", "reverted": False, "reply": "Looked."},
    ]
    events = list(agent_build.step_build(planned))
    assert FakeWorkshop.looks == [False, "only"]
    assert FakeWorkshop.turns[1].startswith("The real images are now in place")
    # grid-1 never arrived: the agent is told to take it off the page
    assert "grid-1" in FakeWorkshop.turns[1] and "hero-1" not in FakeWorkshop.turns[1]
    sent = dict(FakeWorkshop.assets_put)
    assert sent["hero-1.png"] is True and "hero-1--card.png" in sent
    assert "grid-1.png" not in sent
    assert not steps.pending_assets(planned)
    assert events[-1].kind == "done" and (planned.dir / "studio.json").is_file()


def test_a_restart_mid_build_makes_the_images_here_instead(planned, monkeypatch):
    from sparrow import steps

    agent_build.placeholders(planned, steps._bb(planned))      # no thread: as after a restart
    monkeypatch.setattr(steps, "step_assets", _made(planned, {"hero-1", "grid-1"}))
    FakeWorkshop.endings = [
        {"kind": "done", "checkpoint": "abc", "reverted": False, "reply": "Built."},
        {"kind": "done", "checkpoint": "def", "reverted": False, "reply": "Looked."},
    ]
    list(agent_build.step_build(planned))
    assert "could not be made" not in FakeWorkshop.turns[1]


def test_nothing_to_make_builds_with_the_look_as_before(planned, monkeypatch):
    from sparrow import steps

    monkeypatch.setattr(steps, "resolved_plan", lambda run: [dict(PLAN[0])])
    list(agent_build.step_assets(planned))
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": "abc", "reverted": False}]
    list(agent_build.step_build(planned))
    assert FakeWorkshop.looks == [True]


def test_verify_sends_findings_back_then_stops_at_the_preview_gate(project):
    broken = [{"page": "/", "text": "Pricing", "href": "#pricing", "problem": "no such anchor"}]
    FakeWorkshop.links_found = [broken, []]
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": "def"}]
    with pytest.raises(Halt) as h:
        list(agent_build.step_verify(project))
    assert len(FakeWorkshop.turns) == 1 and "#pricing" in FakeWorkshop.turns[0]
    assert h.value.request.gate is Stage.GATE_PREVIEW
    assert "Every automatic check passed" in h.value.request.question
    assert FakeWorkshop.looks == [False], "a fix turn is checked by the guardrails, not by eye"
    assert FakeWorkshop.fresh == [True], "a fix list runs in its own short session"


def test_verify_stops_when_the_agent_declines_the_same_findings(project):
    broken = [{"page": "/", "text": "x", "href": "#x", "problem": "no such anchor"}]
    FakeWorkshop.links_found = [broken] * 5
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": "c"}] * 5
    with pytest.raises(Halt) as h:
        list(agent_build.step_verify(project))
    assert len(FakeWorkshop.turns) == 1
    assert "judged them fine" in h.value.request.question


def test_verify_caps_its_fix_rounds(project):
    rounds = [[{"page": "/", "text": "x", "href": f"#x{i}", "problem": "no such anchor"}]
              for i in range(5)]
    FakeWorkshop.links_found = rounds
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": "c"}] * 5
    with pytest.raises(Halt) as h:
        list(agent_build.step_verify(project))
    assert len(FakeWorkshop.turns) == agent_build.FIX_ROUNDS
    assert "1 check(s) still flag" in h.value.request.question
    assert json.loads((project.dir / "verify-findings.json").read_text())["unfixed"][0]["kind"] == "link"


def test_the_product_names_parts_are_confirmed(project):
    from sparrow import steps
    bb = steps._bb(project)
    bb.brief.product_name = "MananShooter"
    words = agent_build.confirmed(project, bb)
    assert {"manan", "shooter"} <= words
    assert guard.claims_in("<p>Join Manan Shooter</p>", words) == []


def test_claims_go_to_the_owner_not_to_a_fix_round(project, monkeypatch):
    monkeypatch.setattr(guard, "check_claims", lambda site, words: [
        guard.Finding("claim", "src/app/page.tsx", "names or figures the owner never gave: "
                      "Steam, 4.03. If any is a name...")])
    with pytest.raises(Halt) as h:
        list(agent_build.step_verify(project))
    assert FakeWorkshop.turns == [], "no model call for a judgement the owner makes"
    q = h.value.request.question
    assert "Steam" in q and "4.03" in q
    saved = json.loads((project.dir / "verify-findings.json").read_text())
    assert saved["for_owner"][0]["kind"] == "claim" and saved["unfixed"] == []


# ── speed ───────────────────────────────────────────────────────────────────

def test_a_stalled_call_is_hedged_and_the_first_answer_wins():
    import threading
    import time as _t
    from sparrow.providers import hedged
    calls = []
    lock = threading.Lock()

    def call():
        with lock:
            calls.append(1)
            n = len(calls)
        if n == 1:
            _t.sleep(3)          # the stall
            return "late"
        return "quick"

    t0 = _t.time()
    assert hedged(call, after=0.2) == "quick"
    assert _t.time() - t0 < 1.5 and len(calls) == 2


def test_a_prompt_call_is_never_duplicated():
    from sparrow.providers import hedged
    calls = []
    assert hedged(lambda: calls.append(1) or "ok", after=5) == "ok"
    assert calls == [1]


def test_parallel_keeps_input_order():
    import time as _t
    from sparrow import steps
    out = steps.parallel(lambda x: (_t.sleep(0.05 * (3 - x)), x)[1], [0, 1, 2])
    assert out == [0, 1, 2]


def test_a_checkpoint_mid_assets_keeps_the_stand_ins_it_has_not_replaced(planned):
    from sparrow import steps

    agent_build.placeholders(planned, steps._bb(planned))
    hero = next(a for a in steps._bb(planned).assets if a.id == "hero-1")
    real = hero.model_copy(update={"provenance": Provenance.RESTYLED})
    steps._checkpoint_assets(planned, [])
    assert [a.id for a in steps._bb(planned).assets] == ["nav-logo", "hero-1", "grid-1"]
    steps._checkpoint_assets(planned, [real])
    after = {a.id: a for a in steps._bb(planned).assets}
    assert list(after) == ["nav-logo", "hero-1", "grid-1"]
    assert after["hero-1"].provenance == Provenance.RESTYLED


def test_the_owners_extra_images_survive_replanning_and_reach_the_agent(project, monkeypatch):
    from PIL import Image
    from sparrow import steps

    monkeypatch.setattr(steps, "asset_plan", lambda run: [dict(PLAN[1])])
    buf = io.BytesIO()
    Image.effect_noise((1600, 1000), 60).convert("RGB").save(buf, "PNG")
    with pytest.raises(ValueError):
        steps.add_owner_image(project, "a.png", buf.getvalue(), "  ")
    first = steps.add_owner_image(project, "agents.png", buf.getvalue(), "AI agents and chats")
    second = steps.add_owner_image(project, "crm.png", buf.getvalue(), "All the CRM tools")
    assert (first["id"], second["id"]) == ("owner-1", "owner-2")
    plan = steps.merged_plan(project)
    assert [a["id"] for a in plan] == ["hero-1", "owner-1", "owner-2"]
    steps.record_asset_decisions(project, {"hero-1": "generate", "owner-1": "as_is",
                                           "owner-2": "as_is"})
    assert [a["decision"] for a in steps.resolved_plan(project)] == ["generate", "as_is", "as_is"]

    stand_ins = agent_build.placeholders(project, steps._bb(project))
    assert stand_ins == ["hero-1"], "an image used as it is goes in at once"
    assert not agent_build._still_stand_in(project.workspace / "public/assets/owner-1.png")
    text = agent_build.dossier_for(project)
    assert "place it where it fits: AI agents and chats" in text


# ── crop and type ───────────────────────────────────────────────────────────

def test_a_strip_of_a_card_crop_is_a_crop_finding_and_a_whole_image_is_not():
    originals = {"owner-4.png": (1600, 1000), "owner-2.png": (1600, 1000)}
    images = [
        # twenty-crm as measured: a 590x179 cover box over the 800x800 card crop
        {"src": "/p/assets/owner-4--card.png", "natural": [800, 800], "box": [590, 179],
         "visible": 0.30},
        {"src": "/p/assets/owner-2.png?v=1", "natural": [1600, 1000], "box": [583, 484],
         "visible": 0.67},
        {"src": "/p/assets/nav-logo.svg", "natural": [136, 136], "box": [34, 34], "visible": 1},
    ]
    found = guard.check_crops(images, originals)
    assert [(f.kind, f.where) for f in found] == [("crop", "owner-4.png")]
    assert "shows 19%" in found[0].detail and "1600:1000" in found[0].detail


def test_headline_scale_is_held_to_the_main_reference():
    heads = [{"tag": "h1", "size": 74, "text": "Build"}, {"tag": "h2", "size": 53, "text": "x"}]
    assert guard.check_type(heads, ("attio.com", 96))[0].kind == "type"
    assert guard.check_type(heads, ("supabase.com", 46)) == []
    assert guard.check_type(heads, None) == []


def test_reference_scale_reads_the_primarys_largest_measured_size(project):
    (project.dir / "typography.json").write_text(json.dumps({
        "a.com": {"display": {"size": 64}, "heading": {"size": 96}, "mono": "X"},
        "b.com": {"display": {"size": 120}}}))
    assert agent_build.reference_scale(project) == ("a.com", 96.0)
    assert "a.com, sets its largest heading at 96px" in agent_build.dossier_for(project)


def test_verify_sends_crops_and_scale_back_as_fixes(project):
    (project.dir / "typography.json").write_text(json.dumps({"a.com": {"heading": {"size": 96}}}))
    FakeWorkshop.page = {"images": [], "headings": [{"tag": "h1", "size": 60, "text": "x"}]}
    FakeWorkshop.endings = [{"kind": "done", "checkpoint": "f1", "reverted": False}] * 2
    with pytest.raises(Halt):
        list(agent_build.step_verify(project))
    assert "[type] page: the largest heading is 60px" in FakeWorkshop.turns[0]


def test_the_owner_can_name_the_main_reference(project):
    from sparrow import steps

    assert steps.owner_primary(project, ["attio.com", "linear.app"]) is None
    (project.dir / steps.MAIN_REFERENCE).write_text("https://www.attio.com/")
    assert steps.owner_primary(project, ["linear.app", "attio.com"]) == "attio.com"


def test_text_under_an_image_is_one_finding_per_image():
    found = guard.check_covered([
        {"tag": "h3", "text": "Custom data model", "by": "owner-4.png"},
        {"tag": "p", "text": "Create the objects", "by": "owner-4.png"},
        {"tag": "h3", "text": "Hosted or self-hosted", "by": "owner-3.png"}])
    assert [(f.kind, f.where) for f in found] == [("covered", "owner-3.png"),
                                                  ("covered", "owner-4.png")]
    assert "h3 “Custom data model”, p “Create the objects”" in found[1].detail


def test_a_still_page_against_a_moving_direction_is_a_motion_finding(tmp_path):
    (tmp_path / "src/app").mkdir(parents=True)
    page = tmp_path / "src/app/page.tsx"
    page.write_text("export default function P(){return <h1>Still</h1>}")
    (tmp_path / "src/app/globals.css").write_text('@import "tw-animate-css";\n.a{color:red}')
    assert guard.check_motion(tmp_path, "200ms fades")[0].kind == "motion"
    page.write_text('<motion.div whileInView={{opacity: 1}} />')
    assert guard.check_motion(tmp_path, "200ms fades") == []


def test_the_agent_is_told_the_directions_motion_and_treatments():
    bb = _bb()
    assert bb.design_system.motion
    assert f"Its motion, to build, not to describe: {bb.design_system.motion}" in \
        agent_build.direction_note(bb)


# ── arrival ─────────────────────────────────────────────────────────────────

BRIEF_MOTION = """  OTHER
    something
  MOTION
    always-running motion: 2/2  — e.g. cursorBlink, marquee
    interaction tempo: 400ms typical (range 100-400ms)
    ARRIVAL — read off the page, not guessed.
      46% of all elements are staged this way
      they start at opacity 0.00  — from nothing, not a partial fade
      and rise 60px into place
      over 400ms
  ENCLOSURE
    boxed 12%
"""


def test_the_sources_motion_is_read_from_the_design_brief_and_handed_over(project):
    (project.dir / "sources/design-brief.md").write_text(BRIEF_MOTION)
    block, nums = agent_build.source_motion(project)
    assert nums == {"share": 0.46, "from": 0.0, "travel": 60, "ms": 400}
    assert "cursorBlink" in block and "ENCLOSURE" not in block
    assert "How the reference sites move" in agent_build.dossier_for(project)


def test_a_page_that_stages_far_fewer_entrances_than_the_sources_is_a_finding():
    src = {"share": 0.46, "from": 0.0, "travel": 60, "ms": 400}
    found = guard.check_arrival({"share": 0.0}, src)
    assert found[0].kind == "arrival" and "stage 46%" in found[0].detail
    assert "rising 60px, over 400ms" in found[0].detail
    assert guard.check_arrival({"share": 0.3}, src) == []
    assert guard.check_arrival({"share": 0.0}, {"share": 0.04}) == [], "sources barely move"
    assert guard.check_arrival({"share": 0.0}, None) == []
    # staged as one wrapper per block: few elements themselves, most through a parent
    assert guard.check_arrival({"share": 0.10, "reach": 0.55}, src) == []


def test_the_agent_is_told_how_sections_arrive():
    bb = _bb()
    bb.design_system.arrival = "headings rise 15px from opacity 0 over 400ms"
    assert "How each section arrives as the reader reaches it, to build: headings rise" \
        in agent_build.direction_note(bb)

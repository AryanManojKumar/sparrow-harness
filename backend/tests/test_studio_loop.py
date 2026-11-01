"""The studio turn: edit → build → look → one checkpoint, and every way it can fail.

The agent and the build are replaced by recorders, so each branch is reached
deterministically: a clean change, a build the agent repairs, a build it never
repairs (the change must vanish without a trace), and a polish that breaks a
change that had already built (the built change must survive).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparrow import dossier
from sparrow.blackboard.schema import Blackboard
from sparrow.fixtures.ledgerline import BRIEF, CONSTRAINTS, DESIGN_SYSTEM
from sparrow.workshop import look, store, studio
from sparrow.workshop.config import WorkshopConfig


def _project(tmp: Path) -> store.Project:
    ws = tmp / "src-ws"
    (ws / "src/app").mkdir(parents=True)
    (ws / "src/app/page.tsx").write_text("home v1\n")
    (ws / "package.json").write_text("{}")
    proj = store.project(tmp / "root", "site-1")
    store.import_workspace(proj, store.pack(ws))
    return proj


class _Result:
    def __init__(self, text: str) -> None:
        self.final_response = text
        self.finish_reason = "completed"


class _Session:
    """Each prompt pops the next scripted action: (files to write, reply)."""

    def __init__(self, proj: store.Project, script: list[tuple[dict, str]]) -> None:
        self.proj, self.script, self.prompts = proj, list(script), []

    def run(self, prompt, on_notification=None):
        self.prompts.append(prompt)
        files, reply = self.script.pop(0) if self.script else ({}, studio.LOOKS_RIGHT)
        for rel, text in files.items():
            path = self.proj.workspace / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return _Result(reply)


class _Live:
    def __init__(self, session) -> None:
        self.session, self.last_used = session, 0.0


@pytest.fixture
def shop(tmp_path, monkeypatch):
    s = object.__new__(studio.Studio)
    s.cfg = WorkshopConfig(root=tmp_path / "root", token="t" * 32, deps=tmp_path,
                           node=tmp_path, llm_url="http://office/llm/v1")
    builds: list[bool] = []
    monkeypatch.setattr(studio, "build", lambda cfg, proj: {
        "ok": builds.pop(0) if builds else True, "seconds": 0, "log": "Type error: x"})
    monkeypatch.setattr(look, "shoot", lambda export, base, routes: [])
    return s, builds


def _turn(s, proj, session):
    events: list[dict] = []
    done = s._loop(_Live(session), proj, "Add a pricing page", events.append)
    return done, events


def test_a_clean_change_becomes_one_checkpoint(shop, tmp_path):
    s, _ = shop
    proj = _project(tmp_path)
    session = _Session(proj, [({"src/app/pricing/page.tsx": "pricing"}, "Added a pricing page.")])
    done, events = _turn(s, proj, session)
    assert done["checkpoint"] and not done["reverted"]
    assert done["changed"] == ["src/app/pricing/page.tsx"]
    assert [c["message"] for c in store.checkpoints(proj)] == [
        "Add a pricing page", "Imported the generated site"], "intermediate commits are squashed"


def test_a_build_the_agent_repairs_is_kept(shop, tmp_path):
    s, builds = shop
    builds += [False, True]
    proj = _project(tmp_path)
    session = _Session(proj, [({"src/app/pricing/page.tsx": "broken"}, "Added."),
                              ({"src/app/pricing/page.tsx": "fixed"}, "Fixed the build.")])
    done, events = _turn(s, proj, session)
    assert done["checkpoint"] and not done["reverted"]
    assert "Type error: x" in session.prompts[1], "the repair turn sees the build log"
    assert (proj.workspace / "src/app/pricing/page.tsx").read_text() == "fixed"
    assert {"kind": "status", "text": "fixing a build error"} in events


def test_a_change_that_never_builds_vanishes(shop, tmp_path):
    s, builds = shop
    builds += [False, False, False, True]   # three failures, then the restore build
    proj = _project(tmp_path)
    session = _Session(proj, [({"src/app/page.tsx": "home broken",
                                "src/app/new/page.tsx": "new"}, "Changed it."),
                              ({}, "Tried."), ({}, "Tried again.")])
    done, _ = _turn(s, proj, session)
    assert done["reverted"] and done["checkpoint"] is None and done["changed"] == []
    assert (proj.workspace / "src/app/page.tsx").read_text() == "home v1\n"
    assert not (proj.workspace / "src/app/new").exists()
    assert [c["message"] for c in store.checkpoints(proj)] == ["Imported the generated site"]


def test_a_polish_that_breaks_the_build_keeps_the_built_change(shop, tmp_path, monkeypatch):
    s, builds = shop
    builds += [True, False, False, True]    # change ok; polish fails twice; restore build
    monkeypatch.setattr(look, "shoot", lambda export, base, routes:
                        [{"route": "/", "part": 1, "of": 1, "data": "AAAA"}])
    proj = _project(tmp_path)
    session = _Session(proj, [({"src/app/page.tsx": "home v2"}, "Updated the home page."),
                              ({"src/app/page.tsx": "home v3 broken"}, "Polished spacing."),
                              ({}, "Tried to fix.")])
    done, _ = _turn(s, proj, session)
    assert not done["reverted"] and done["checkpoint"]
    assert (proj.workspace / "src/app/page.tsx").read_text() == "home v2"
    image_turn = session.prompts[1]
    assert any(b.get("type") == "image" for b in image_turn), "the agent is shown the page"


def test_no_change_means_no_checkpoint(shop, tmp_path):
    s, _ = shop
    proj = _project(tmp_path)
    done, _ = _turn(s, proj, _Session(proj, [({}, "That is already how it reads.")]))
    assert done["checkpoint"] is None and not done["reverted"]
    assert len(store.checkpoints(proj)) == 1


# ── routes to look at ──────────────────────────────────────────────────────

def test_routes_for_changed_files():
    assert look.routes_for(["src/app/pricing/page.tsx"]) == ["/pricing/"]
    assert look.routes_for(["src/components/sections/Footer.tsx"]) == ["/"]
    assert look.routes_for(["src/app/page.tsx"]) == ["/"]
    assert look.routes_for(["src/app/(marketing)/about/page.tsx",
                            "src/components/sections/Nav.tsx"]) == ["/", "/about/"]
    assert look.routes_for(["src/app/blog/[slug]/page.tsx"]) == ["/"]


# ── dossier ─────────────────────────────────────────────────────────────────

def _bb() -> Blackboard:
    return Blackboard(project_id="ledger", brief=BRIEF, constraints=CONSTRAINTS,
                      design_system=DESIGN_SYSTEM)


def test_dossier_carries_the_record_and_the_build_rules():
    content = {"hero": {"slots": {"headline": "Close the books", "stat": "40% faster"},
                        "provenance": {"headline": "drafted", "stat": "user_supplied"}}}
    text = dossier.render(_bb(), content, "/projects/ledger/preview")
    for c in CONSTRAINTS:
        assert f'"{c.text}"' in text, "constraints are verbatim"
    for color in DESIGN_SYSTEM.colors:
        assert f"`{color.token}`" in text
    assert DESIGN_SYSTEM.type_steps[0].classes in text
    assert "/projects/ledger/preview/assets/" in text
    assert "next/link" in text
    confirmed = text.split("Confirmed by the owner:")[1].split("Drafted")[0]
    assert "40% faster" in confirmed and "Close the books" not in confirmed


def test_dossier_is_read_only_history_aware_and_outside_checkpoints(tmp_path):
    proj = _project(tmp_path)
    (proj.workspace / "src/app/page.tsx").write_text("v2")
    store.checkpoint(proj, "Made the headline shorter")
    store.write_dossier(proj, "# Site\n")
    text = proj.dossier.read_text()
    assert "Made the headline shorter" in text and "Imported the generated site" not in text
    assert store.changed_files(proj) == [], "AGENTS.md is not part of the site's history"
    store.undo(proj)
    assert proj.dossier.is_file(), "undo does not roll back what the agent is told"


def test_a_model_that_never_answers_is_an_error_not_a_silent_done(shop, tmp_path):
    """Rate-limited upstream: the runtime ends the turn with finish_reason "error"
    and no text. That must surface, not read as "nothing needed changing"."""
    s, _ = shop
    proj = _project(tmp_path)

    class Silent:
        def run(self, prompt, on_notification=None):
            r = _Result("")
            r.finish_reason = "error"
            return r

    with pytest.raises(studio.ModelUnavailable):
        _turn(s, proj, Silent())

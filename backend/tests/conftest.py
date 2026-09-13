"""Shared scaffolding for the harness tests.

Everything here is deterministic: no model call, no browser, no network, no
money. The stages under test reach for the expensive things through
module-level names — `sparrow.steps._inspect_once`, `sparrow.agents.builder.Fixer`,
`sparrow.cli._run_build` — so a test replaces the NAME rather than trying to
make the real thing cheap. That is also why the fakes below are recorders: the
bugs these tests exist for are both "something was computed and then not
handed on", which is only visible if you can see what the next stage received.
"""

from __future__ import annotations

from pathlib import Path

from sparrow.blackboard.schema import Blackboard, Section
from sparrow.fixtures.ledgerline import BRIEF, CONSTRAINTS, DESIGN_SYSTEM
from sparrow.orchestrator import Run

SECTIONS_DIR = "src/components/sections"


def component_name(section_id: str) -> str:
    """The same derivation `steps.step_sources` uses, so paths match production."""
    return "".join(w.capitalize() for w in section_id.replace("-", " ").split())


def make_run(root: Path, files: dict[str, str], *, pid: str = "t") -> Run:
    """A project on disk with a real blackboard and real section files.

    `files` maps section id -> the .tsx source that section starts with. The
    design system is the ledgerline fixture, which is the only one in the repo
    with measured audit results attached to it.
    """
    d = root / "projects" / pid
    ws = d / "workspace"
    (ws / SECTIONS_DIR).mkdir(parents=True, exist_ok=True)
    (ws / "out").mkdir(parents=True, exist_ok=True)

    sections = []
    for order, (sid, code) in enumerate(files.items(), 1):
        comp = component_name(sid)
        sections.append(Section(
            id=sid, order=order, blueprint_id=sid,
            target_path=f"{SECTIONS_DIR}/{comp}.tsx", component_name=comp,
        ))
        (ws / SECTIONS_DIR / f"{comp}.tsx").write_text(code)

    bb = Blackboard(project_id=pid, brief=BRIEF, constraints=list(CONSTRAINTS),
                    design_system=DESIGN_SYSTEM, sections=sections)
    (d / "blackboard.json").write_text(bb.model_dump_json(indent=2))
    (d / "blueprints").mkdir(exist_ok=True)
    return Run(pid, root, {})


# ------------------------------------------------------------------- fakes


class _Usage:
    def cost(self, *_a, **_k) -> float:
        return 0.0


class _Provider:
    name = "fake"


class _Output:
    def __init__(self, code: str) -> None:
        self.code = code
        self.usage = _Usage()


class RecordingFixer:
    """Stands in for `Fixer`, and remembers exactly what it was handed.

    `calls` is the whole point: Bug A is that drift findings never reach this
    argument, and the only way to prove that is to look at the argument.
    """

    provider = _Provider()
    tier = "fake"

    def __init__(self, replies: dict[str, str] | None = None,
                 disputes: dict[str, str] | None = None) -> None:
        self.calls: list[tuple[str, list]] = []
        self.replies = replies or {}
        self.disputes = disputes or {}

    def fix(self, _bb, section, code: str, defects: list):
        self.calls.append((section.id, list(defects)))
        if section.id in self.disputes:
            return _Output(code), self.disputes[section.id]
        return _Output(self.replies.get(section.id, code)), None

    def codes(self) -> set[str]:
        return {getattr(d, "code", "?") for _sid, ds in self.calls for d in ds}


class RecordingBuilder:
    """Stands in for `Builder`, and remembers which sections it was asked for.

    `calls` is the whole point, again: resume is the claim that a BUILT section
    is not sent to the builder a second time, and the only evidence for that is
    the list of sections the builder was handed. A fake that merely writes files
    would let a rebuild-everything pass as a resume.

    `on_build` runs before the code is returned, so a test can kill the stage
    part-way through and look at what the blackboard says at that instant.
    """

    provider = _Provider()
    tier = "fake"

    def __init__(self, code: str = "export default function S() { return null; }\n",
                 on_build=None) -> None:
        self.calls: list[str] = []
        # Everything `step_build` hands over, per section. Identity and the
        # asset list are both computed in the step and consumed in the agent,
        # which is exactly the "computed and then not handed on" seam this file
        # exists to keep visible.
        self.kwargs: dict[str, dict] = {}
        self.code = code
        self.on_build = on_build

    def build(self, _bb, section, _bp, **_kw):
        self.calls.append(section.id)
        self.kwargs[section.id] = _kw
        if self.on_build is not None:
            self.on_build(section)
        return _Output(self.code.replace("function S", f"function {section.component_name}"))


def install_build(monkeypatch, builder, *, blueprints=None, compose=None, repair=None):
    """Swap out everything in `step_build` that costs money or runs pnpm."""
    import sparrow.agents.builder as builder_mod
    import sparrow.blueprints as blueprints_mod
    import sparrow.cli as cli_mod
    from sparrow.blackboard.schema import Blueprint

    monkeypatch.setattr(builder_mod, "Builder", lambda: builder)
    monkeypatch.setattr(
        blueprints_mod, "load_dir",
        lambda _d: blueprints if blueprints is not None
        else _every_section_has_one(_d))
    monkeypatch.setattr(cli_mod, "_compose_page", compose or (lambda _bb, _ws: None))
    # (built, spent) since the loop began reporting whether the workspace
    # actually compiles — the default stub says it did.
    monkeypatch.setattr(cli_mod, "_repair_until_builds",
                        repair or (lambda _bb, _ws, _p: (True, 0.0)))
    return Blueprint


def blueprints_for(*ids):
    from sparrow.blackboard.schema import Blueprint

    return {i: Blueprint(id=i, purpose="p", slots=["headline"], structure="s")
            for i in ids}


def _every_section_has_one(_d):
    raise AssertionError("pass blueprints= to install_build")


def read_bb(run):
    """The blackboard as it stands on disk, right now."""
    return Blackboard.model_validate_json(run.blackboard_path.read_text())


def drain(gen):
    """Run a stage generator to its gate. Returns (events, GateRequest)."""
    from sparrow.orchestrator import Halt

    events = []
    try:
        for ev in gen:
            events.append(ev)
    except Halt as h:
        return events, h.request
    return events, None

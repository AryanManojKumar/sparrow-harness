"""The stage implementations the orchestrator drives.

Each is a generator yielding `Event`s, so a caller sees progress during a stage
that takes minutes. Each raises `Halt` at a gate.

These wrap the same agents the CLI has been calling by hand all along; nothing
here is new capability. What is new is that the ORDER is written down once,
rather than living in whoever is typing the commands.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

from sparrow.blackboard.schema import Blackboard, BuildStatus, Ground, Section
from sparrow.blackboard.store import Rejected, Store
from sparrow.orchestrator import Event, GateRequest, Halt, Run, Stage

CHROME_SKIP_ASSETS = {"nav", "footer"}


CHROME_ORDER = ("nav", "footer")

STACK = (
    "Next.js 16 App Router, static export. React 19. TypeScript. Tailwind v4. "
    "Motion 13 from 'motion/react'. Icons from 'lucide-react'. "
    "next/image with `unoptimized` (static export)."
)


def _bb(run: Run) -> Blackboard:
    return Blackboard.model_validate_json(run.blackboard_path.read_text())


# --------------------------------------------------------------- one write path
#
# CLAUDE.md §3: agents propose diffs, an orchestrator applies or rejects them,
# and every state transition is recorded so a run is replayable. `Store.apply` is
# that mechanism and until now these step functions went around it — `_save` did
# `bb.version += 1` and dumped the whole model over the file. Measured across the
# six exported projects, that is exactly what the blackboard shows: `version`
# climbing (brief, sources, design all went through `_save`) and `decisions`
# empty on every one, because the decision log only ever gets written by the path
# nothing was using.
#
# Everything below routes through `Store.apply`. That buys three things `_save`
# could not: the patch is validated against the schema before it lands, the write
# is atomic (see `Store._write`), and each transition leaves a Decision naming
# the agent that caused it.
#
# A rejection is NOT raised. Persistence must never change what a run produces —
# a build that succeeded and then failed to record itself is still a build that
# succeeded, and turning a bookkeeping failure into a dead stage would be a worse
# bug than the one this fixes. Callers surface the rejection as a `blocked` event
# and carry on.


# The prefix that identifies an adoption in the decision log, so a later
# adoption can name the one it supersedes without re-deriving what "adopted"
# looks like in two places.
_ADOPTED = "direction adopted: #"


def _store(run: Run) -> Store:
    return Store(run.blackboard_path)


def telemetry_note(run: Run, where: str, rejected: Rejected) -> None:
    """Where a rejection cannot become an Event, it still has to become a line.

    `adopt_direction` and `record_asset_decisions` are called from the HTTP layer,
    not from inside a stage generator, so there is nothing to yield into. A
    rejection swallowed here is a decision that silently did not get logged,
    which is the exact class of bug this work exists to close.
    """
    from sparrow import telemetry

    telemetry.log_stage("blackboard", "blocked",
                        f"{where}: {rejected.code} — {rejected.message}")


def _note(run: Run, *, agent: str, summary: str,
          supersedes: str | None = None) -> Rejected | None:
    """Record a decision that changes no other field.

    An empty patch is deliberate: the decision IS the state change. A Fixer
    dispute moves nothing on the blackboard and is precisely the thing that was
    unrecoverable afterwards — one run burned three rounds and ~$2 on four
    disputes whose text existed only in a `disputed` dict that died with the
    process.
    """
    r = _store(run).apply([], agent=agent, summary=_safe(summary),
                          supersedes=supersedes)
    return r if isinstance(r, Rejected) else None


# Decisions are read back by agents, rendered into prompts and copied into logs.
# `Asset.scrubbed` already carries the rule for the same reason: record the shape
# of a thing, never the value. Nothing here composes user text into a summary —
# the summaries are section ids, status names, defect codes and agent-authored
# prose about code — and the cap keeps a runaway model reply from turning the
# decision log into the biggest field on the blackboard.
_SUMMARY_MAX = 400


def _safe(summary: str) -> str:
    one_line = " ".join(summary.split())
    return one_line if len(one_line) <= _SUMMARY_MAX else one_line[:_SUMMARY_MAX - 1] + "…"


def _replace(run: Run, path: str, value, *, agent: str, summary: str,
             supersedes: str | None = None) -> Rejected | None:
    """Replace one top-level field. The shape every old `_save` call really had."""
    r = _store(run).apply([{"op": "replace", "path": path, "value": value}],
                          agent=agent, summary=_safe(summary), supersedes=supersedes)
    return r if isinstance(r, Rejected) else None


def _record_section(run: Run, section_id: str, *, agent: str,
                    status: BuildStatus | None = None,
                    bump_attempt: bool = False,
                    defects: list[str] | None = None,
                    note: str = "") -> Rejected | None:
    """Move one section's build state, immediately, as it moves.

    Per section rather than per stage. `step_build` used to write nothing at all
    until the stage ended, so a run that died on section six left nine sections
    reading `pending / 0 attempts` — an accurate record of a build that never
    happened, on a project with six built files on disk. That record is what
    resume reads, so it has to be true at every instant, not only at the end.

    The index is resolved against a FRESH read rather than against the caller's
    in-memory blackboard: by the time a build reaches section six the caller's
    copy is five versions stale, and an index taken from it points at whatever
    happens to sit there now.
    """
    bb = _bb(run)
    idx = next((i for i, s in enumerate(bb.sections) if s.id == section_id), None)
    if idx is None:
        return Rejected("unknown-section",
                        f"no section {section_id!r} on this blackboard")
    current = bb.sections[idx]

    patch: list[dict] = []
    parts: list[str] = []
    if status is not None and status is not current.status:
        patch.append({"op": "replace", "path": f"/sections/{idx}/status",
                      "value": status.value})
        parts.append(f"{current.status.value} → {status.value}")
    if bump_attempt:
        patch.append({"op": "replace", "path": f"/sections/{idx}/attempts",
                      "value": current.attempts + 1})
        parts.append(f"attempt {current.attempts + 1}")
    if defects is not None and defects != current.defects:
        patch.append({"op": "replace", "path": f"/sections/{idx}/defects",
                      "value": [_safe(d) for d in defects]})
        parts.append(f"{len(defects)} defect(s)" if defects else "defects cleared")

    if not patch and not note:
        return None                      # nothing moved; do not bump the version
    summary = f"{section_id}: " + " · ".join([*parts, *( [note] if note else [] )])
    r = _store(run).apply(patch, agent=agent, summary=_safe(summary))
    return r if isinstance(r, Rejected) else None


def reset_sections(run: Run, section_ids: list[str]) -> list[str]:
    """Send named sections back to PENDING so a re-advance rebuilds only those.

    The user-facing half of resume: "just redo the hero". Without it, persisted
    state means a resumed run skips every built section forever and there is no
    way to ask for one of them again.

    Raises ValueError on an unknown id rather than silently resetting nothing —
    a typo that reports success and rebuilds nothing is the failure this is
    for.
    """
    bb = _bb(run)
    known = {s.id for s in bb.sections}
    unknown = sorted(set(section_ids) - known)
    if unknown:
        raise ValueError(f"no such section(s): {', '.join(unknown)}")
    done = []
    for sid in section_ids:
        _record_section(run, sid, agent="orchestrator", status=BuildStatus.PENDING,
                        defects=[], note="reset for rebuild at the user's request")
        done.append(sid)
    return done


# ------------------------------------------------------------------ gate 1

def step_brief(run: Run) -> Iterator[Event]:
    bb = _bb(run)
    if bb.brief is None:
        raise Halt(GateRequest(
            Stage.GATE_BRIEF,
            "What are we building, and who is it for?",
            options=[], artifacts=[],
        ))
    yield Event(Stage.BRIEF, "progress",
                f"{bb.brief.category} · {len(bb.active_constraints())} constraint(s)")


# ------------------------------------------------------------------ sources

def step_sources(run: Run, urls: list[str]) -> Iterator[Event]:
    from sparrow.agents.blueprinter import Blueprinter, to_markdown
    from sparrow.providers import Tier, get_provider
    from sparrow.rank import (RANKABLE, Candidate, commonality, pick_primary,
                              rank_section, to_design_brief)
    from sparrow.scout import classify, extract

    bb = _bb(run)
    provider = get_provider()
    labelled: dict[str, list[tuple[str, int]]] = {}
    by_type: dict[str, list[Candidate]] = {}
    by_type_all: dict[str, list[Candidate]] = {}   # includes chrome, for blueprints
    registers: dict[str, object] = {}
    out_dir = run.dir / "sources"

    for url in urls:
        site = url.split("//")[-1].split("/")[0]
        r = extract(url, out_dir, shots=False)
        if not r.ok or len(r.bands) < 4:
            yield Event(Stage.SOURCES, "blocked",
                        f"{site}: unreadable or too thin — skipped")
            continue
        if r.register is not None:
            registers[site] = r.register
        types = classify(provider, r.bands)
        labelled[site] = [(t, b.index + 1) for t, b in zip(types, r.bands)]
        for t, b in zip(types, r.bands):
            cand = Candidate(site, t, b.index + 1, b.height, b.words, b.images,
                             b.buttons, b.listItems, b.headings, b.text, b.unrendered)
            by_type_all.setdefault(t, []).append(cand)
            if t in RANKABLE:
                by_type.setdefault(t, []).append(cand)
        yield Event(Stage.SOURCES, "progress", f"{site}: {len(r.bands)} sections")

    if len(labelled) < 2:
        raise RuntimeError("need at least two readable sources to rank")

    # Keep the measured palettes so the design gate can show them without refetching.
    from dataclasses import asdict
    pals = {s: asdict(r.palette) for s, r in registers.items()
            if getattr(r, "palette", None)}
    if pals:
        (out_dir / "palettes.json").write_text(json.dumps(pals, indent=2))

    comm = commonality(labelled)
    primary, why, usage = pick_primary(provider, bb.brief, labelled)
    yield Event(Stage.SOURCES, "progress", f"primary reference: {primary}",
                cost=usage.cost(provider.name, Tier.CHEAP))

    rankings: dict[str, dict] = {}
    for t in comm.typical_order:
        if not by_type.get(t):
            continue
        r, u = rank_section(provider, bb.brief, t, by_type[t])
        rankings[t] = r
        if u is not None:
            run.spent += u.cost(provider.name, Tier.CHEAP)

    (out_dir / "design-brief.md").write_text(
        to_design_brief(comm, primary, why, rankings, registers))

    bp_dir = run.dir / "blueprints"
    bp_dir.mkdir(parents=True, exist_ok=True)
    bper = Blueprinter(provider)
    order = comm.typical_order

    # Chrome gets blueprints too, written from whatever the sources showed even
    # though it was never ranked.
    for name in CHROME_ORDER:
        cands = by_type_all.get(name, [])
        stub = {"winner": cands[0].site if cands else None,
                "why": "page chrome — required on every page, not ranked",
                "adopt": [], "unopposed": True}
        bp, u = bper.write(bb.brief, name, stub, cands,
                           [x for x in order if x in rankings])
        comp = "".join(w.capitalize() for w in name.replace("-", " ").split())
        (bp_dir / f"{'00' if name == 'nav' else '99'}-{name}.md").write_text(
            to_markdown(bp, comp))
        run.spent += u.cost(provider.name, bper.tier)
        yield Event(Stage.SOURCES, "progress", f"chrome blueprint: {name}")

    for i, t in enumerate(order):
        if t not in rankings:
            continue
        bp, u = bper.write(bb.brief, t, rankings[t], by_type.get(t, []),
                           [x for x in order if x != t])
        comp = "".join(w.capitalize() for w in t.replace("-", " ").split())
        (bp_dir / f"{i + 1:02d}-{t}.md").write_text(to_markdown(bp, comp))
        run.spent += u.cost(provider.name, bper.tier)

    # Nav first, footer last, content between. Chrome is not ranked — every source
    # has both, so "which site does a footer best" is not a question — but it is
    # always built, because a page without navigation is not a page.
    from sparrow.rank import CHROME

    content = [t for t in order if t in rankings]
    sitemap = ["nav", *content, "footer"]
    bb.sections = [
        Section(id=t, order=i, blueprint_id=t,
                target_path=f"src/components/sections/"
                            f"{''.join(w.capitalize() for w in t.replace('-', ' ').split())}.tsx",
                component_name="".join(w.capitalize() for w in t.replace("-", " ").split()),
                # Every section on the page ground by default. Measured: wise,
                # stripe and linear all use ONE ground for the entire page and
                # never alternate. Forcing alternation banded our output into
                # nine visible blocks, which is most of what "it does not flow
                # like the sources" turned out to mean. If a design direction
                # wants a ground change it can ask for one; the default no
                # longer imposes it.
                ground=Ground.PAGE)
        for i, t in enumerate(sitemap, 1)
    ]
    rejected = _replace(run, "/sections",
                        [s.model_dump(mode="json") for s in bb.sections],
                        agent="blueprinter",
                        summary=f"sitemap fixed: {len(bb.sections)} sections — "
                                + ", ".join(s.id for s in bb.sections))
    if rejected:
        yield Event(Stage.SOURCES, "blocked",
                    f"sitemap not recorded ({rejected.code}): {rejected.message}")
    yield Event(Stage.SOURCES, "done",
                f"{len(bb.sections)} sections · {len(rankings)} blueprints")


# ------------------------------------------------------------------ gate 2

def step_design(run: Run, alternatives: int = 3) -> Iterator[Event]:
    """Propose several directions, then stop. Re-rolling gives the same answer.

    Measured in experiments/variance-01: three runs on identical inputs produced
    byte-identical design systems. A gate whose "no" changes nothing is not a gate,
    so the options are generated up front and the human picks between them.
    """
    from sparrow.agents.design_director import DesignDirector

    bb = _bb(run)
    sources = (run.dir / "sources" / "design-brief.md").read_text()

    # If the last gate was answered "none of these", the note steers this pass.
    redirect = run.dir / "redirect.txt"
    if redirect.exists():
        sources += ("\n\n<the_user_rejected_the_previous_directions>\n"
                    f"They asked for: {redirect.read_text().strip()}\n"
                    "Take that seriously and literally. It is a correction to the "
                    "direction, not a nuance to blend in.\n"
                    "</the_user_rejected_the_previous_directions>")
        redirect.unlink()
        # The FACT of the re-roll, never the sentence they typed. The steer
        # itself is the user's own words about their own business and the
        # decision log is read into prompts and copied into logs; the design
        # system this produces is where that steer becomes visible and
        # inspectable. What is unrecoverable without this line is that these
        # three directions are a second set, not the first.
        rejected = _note(run, agent="design-director",
                         summary="previous directions rejected at gate 2 — "
                                 "re-proposing against the user's correction")
        if rejected:
            yield Event(Stage.DESIGN, "blocked",
                        f"re-roll not recorded ({rejected.code}): {rejected.message}")

    dd = DesignDirector()
    proposals, seen = [], []
    for i in range(alternatives):
        ds, revised, u = dd.direct(bb, sources=sources, avoid=seen or None)
        seen.append(ds)
        proposals.append({"index": i, "signature": ds.signature,
                          "atmosphere": ds.atmosphere,
                          "type": f"{ds.font_display} / {ds.font_body}",
                          "revised": revised,
                          "design_system": ds.model_dump(mode="json")})
        yield Event(Stage.DESIGN, "progress", f"direction {i + 1}: {ds.signature[:64]}",
                    cost=u.cost(dd.provider.name, dd.tier))

    (run.dir / "directions.json").write_text(json.dumps(proposals, indent=2))

    # Render each direction, and what the sources are actually painted with.
    # This gate fixes every visual decision downstream, and it was being asked in
    # language only the design agent understands — "a perforated remittance-advice
    # ribbon carrying real currency pairs". §8 wants concrete options a business
    # owner can answer, and swatches are answerable where that sentence is not.
    from sparrow.specimen import direction_html, render, sources_html

    html = {f"direction-{i}": direction_html(seen[i], i) for i in range(len(seen))}
    pals = {s: r.palette for s, r in _source_palettes(run).items()}
    if pals:
        html["sources"] = sources_html(pals)
    for r in render(html, run.dir / "specimens"):
        yield Event(Stage.DESIGN, "progress", f"specimen: {r.name}")

    prefix = f"/projects/{run.project_id}/specimens"
    dark_count = sum(1 for p in pals.values() if p.dark)
    raise Halt(GateRequest(
        Stage.GATE_DESIGN,
        "Which direction should the site take?"
        + (f"  ({dark_count} of {len(pals)} of your reference sites use a dark ground.)"
           if pals else ""),
        options=[
            *[{**{k: p[k] for k in ("index", "signature", "atmosphere", "type")},
               "specimen": f"{prefix}/direction-{p['index']}.png"}
              for p in proposals],
            {"index": -1, "choice": "other",
             "signature": "None of these — describe what you want instead",
             "atmosphere": "Say what to change (darker, warmer, bolder, less green) "
                           "and three new directions are proposed against it.",
             "type": "", "specimen": None},
        ],
        artifacts=[str(run.dir / "specimens"),
                   *( [f"{prefix}/sources.png"] if pals else [] )],
    ))


def _source_palettes(run: Run) -> dict:
    """Re-read the palettes captured during SOURCES, without re-fetching."""
    p = run.dir / "sources" / "palettes.json"
    if not p.exists():
        return {}
    from sparrow.scout import Palette

    return {site: type("R", (), {"palette": Palette(**d)})()
            for site, d in json.loads(p.read_text()).items()}


def adopt_direction(run: Run, index: int) -> None:
    """Write the chosen direction onto the blackboard AND into the workspace.

    Writing it to the blackboard alone is what the first real run did, and the
    design system then never reached the files: no tokens in globals.css, no font
    families bound in layout.tsx. Adopting a direction has to mean both.
    """
    from sparrow.blackboard.schema import DesignSystem

    proposals = json.loads((run.dir / "directions.json").read_text())
    bb = _bb(run)
    chosen = DesignSystem.model_validate(proposals[index]["design_system"])

    # A re-roll ("none of these") replaces a direction that was already adopted,
    # and a replacement is not an addition — CLAUDE.md §4. The trace is the one
    # line that makes "why does this look different from what I approved"
    # answerable after the fact, so the superseded decision is named rather than
    # left to be inferred from two adoptions in a row.
    previous = next((d.id for d in reversed(bb.decisions)
                     if d.summary.startswith(_ADOPTED)), None)
    bb.design_system = chosen
    rejected = _replace(run, "/design_system", chosen.model_dump(mode="json"),
                        agent="design-director",
                        summary=f"{_ADOPTED}{index} — {chosen.signature}",
                        supersedes=previous)
    if rejected:                       # recorded or not, the direction is adopted
        telemetry_note(run, "adopt_direction", rejected)
    apply_design_system(run, bb)


def apply_design_system(run: Run, bb: Blackboard) -> None:
    """Render the design system into globals.css and bind its fonts in layout.tsx."""
    from sparrow.render.tokens import apply_to_stylesheet, font_imports

    ws = run.workspace
    css_path = ws / "src/app/globals.css"
    css_path.write_text(apply_to_stylesheet(css_path.read_text(), bb.design_system))

    imp, consts, rest = font_imports(bb.design_system)
    cls, theme = rest.split("|||")
    layout = ws / "src/app/layout.tsx"
    src = layout.read_text()
    src = re.sub(r'import \{[^}]*\} from "next/font/google";\n', "", src)
    src = re.sub(r"const \w+ = \w+\(\s*\{\s*subsets.*?\}\s*\);\n", "", src, flags=re.S)
    src = src.replace('import "./globals.css";', f'import "./globals.css";\n{imp}\n{consts}')
    src = re.sub(r"\s*// Font families are bound[^\n]*\n", "\n    ", src)
    src = re.sub(r'<html lang="en"[^>]*>',
                 f'<html lang="en" className={{cn("font-body", `{cls}`)}}>', src)
    if "@/lib/utils" not in src:
        src = src.replace('import "./globals.css";',
                          'import "./globals.css";\nimport { cn } from "@/lib/utils";')
    layout.write_text(src)

    css = css_path.read_text()
    css = re.sub(r"\n *--font-(display|body|mono): [^;]+;", "", css)
    css_path.write_text(css.replace("@theme inline {", f"@theme inline {{\n{theme}"))


# ------------------------------------------------------------------ build

# ------------------------------------------------------------- the asset gate

CONTENT_FILE = "content.json"


def load_content(run: Run) -> dict:
    f = run.dir / CONTENT_FILE
    return json.loads(f.read_text()) if f.exists() else {}


def save_content(run: Run, content: dict) -> None:
    (run.dir / CONTENT_FILE).write_text(json.dumps(content, indent=2))


def step_content(run: Run) -> Iterator[Event]:
    """Draft the copy for every section, and collect what it had to invent.

    CLAUDE.md §2's second differentiator. Before this stage the builder wrote
    copy inline from one line of instruction and recorded nothing about which
    claims were invented; the only user words that reached a page were hard
    constraints, pasted verbatim.

    It runs BEFORE the material gate rather than after, so the handful of
    questions it raises can ride along with the image questions instead of
    opening a fifth gate. §8 allows three, and a run with five stops is a run
    nobody finishes.

    Kept in a sidecar next to the asset plan rather than on the blackboard.
    §3 lists `content` as a blackboard field and it should end up there, but
    that is a schema change and this is not — the asset plan established the
    pattern and consistency is worth more here than purity.
    """
    from sparrow.agents.content_editor import ContentEditor
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    existing = load_content(run)
    blueprints = load_dir(run.dir / "blueprints")
    editor = ContentEditor()

    content: dict = {}
    asks = 0
    for section in sorted(bb.sections, key=lambda x: x.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None or not bp.slots:
            continue
        # A resumed run must not redraft copy the user has already answered on.
        prior = existing.get(section.id)
        if prior and prior.get("answered"):
            content[section.id] = prior
            continue

        copy = editor.write(bb.brief, bb.constraints, bp, section_id=section.id)
        content[section.id] = {
            "slots": copy.slots,
            "provenance": {k: v.value for k, v in copy.provenance.items()},
            "asks": [vars(a) for a in copy.asks],
            "answered": False,
        }
        asks += len(copy.asks)
        yield Event(Stage.CONTENT, "progress",
                    f"{section.id}: {len(copy.slots)} slot(s)"
                    + (f", {len(copy.asks)} to confirm" if copy.asks else ""))

    save_content(run, content)
    yield Event(Stage.CONTENT, "done",
                f"copy drafted for {len(content)} section(s) · "
                f"{asks} invented fact(s) to confirm")


def content_asks(run: Run) -> list[dict]:
    """Every unanswered ask across the run, flattened for the gate."""
    out: list[dict] = []
    for sid, entry in load_content(run).items():
        if entry.get("answered"):
            continue
        out += list(entry.get("asks") or [])
    return out


def record_content_answers(run: Run, answers: dict[str, str]) -> int:
    """Apply the gate's content answers. An empty answer keeps the draft.

    Returns how many slots the user actually replaced. Raises ValueError on an
    ask id that does not exist, because a silently ignored answer is worse than
    a refused one — the user typed a real fact about their business and would
    never learn it was dropped.
    """
    content = load_content(run)
    known = {a["id"] for e in content.values() for a in (e.get("asks") or [])}
    unknown = sorted(set(answers) - known)
    if unknown:
        raise ValueError(f"no such content ask(s): {', '.join(unknown)}")

    replaced = 0
    for entry in content.values():
        for ask in list(entry.get("asks") or []):
            answer = (answers.get(ask["id"]) or "").strip()
            if answer:
                entry["slots"][ask["slot"]] = answer
                entry["provenance"][ask["slot"]] = "user_supplied"
                replaced += 1
        entry["asks"] = []
        entry["answered"] = True
    save_content(run, content)
    return replaced


ASSET_PLAN = "asset-plan.json"
DECISIONS = ("upload", "generate", "skip")


def _prominence(count: int, index: int):
    """How large an image sits in its section.

    One image owns the section it is in; after that the first is supporting and
    the rest are thumbnails. Derived in ONE place because the gate has to tell
    the user how large their upload will appear, and a gate that promises
    "dominant" for an image the curator then records as a thumbnail has told
    them something untrue.
    """
    from sparrow.blackboard.schema import Prominence

    if count == 1:
        return Prominence.DOMINANT
    return Prominence.SUPPORTING if index == 1 else Prominence.THUMBNAIL


def asset_plan(run: Run) -> list[dict]:
    """Every image the blueprints asked for, as a list that can be decided on.

    Enumerated once, at the gate, and written to disk; `step_assets` then
    EXECUTES this list rather than re-deriving it from the blueprints. Deriving
    it twice is how a gate ends up offering a choice about an image the curator
    never makes, or making one the user was never asked about.
    """
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    blueprints = load_dir(run.dir / "blueprints")
    out: list[dict] = []
    for section in sorted(bb.sections, key=lambda s: s.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None or not bp.assets:
            continue
        # Chrome asks for a wordmark, which is the user's real brand asset, not
        # something to invent. Generating one produced a 1536x1024 "logo lockup"
        # that the nav then rendered at DOMINANT prominence — a full-width blank
        # box above the hero, which is what "the site looks broken" turned out
        # to mean. A logo belongs to the client; the harness does not draw it.
        if section.id in CHROME_SKIP_ASSETS:
            continue
        for i, brief in enumerate(bp.assets, 1):
            out.append({
                "id": f"{section.id}-{i}", "section_id": section.id, "brief": brief,
                "prominence": _prominence(len(bp.assets), i).value,
                "decision": None, "upload": None,
            })
    return out


def load_plan(run: Run) -> list[dict]:
    p = run.dir / ASSET_PLAN
    return json.loads(p.read_text()) if p.exists() else []


def save_plan(run: Run, plan: list[dict]) -> None:
    (run.dir / ASSET_PLAN).write_text(json.dumps(plan, indent=2))


def step_asset_gate(run: Run) -> Iterator[Event]:
    """Ask, per image, whose it is.

    CLAUDE.md §2 names real material as the differentiator, and until this gate
    existed there was no moment in the run at which a user could hand the system
    a file. The curator read each blueprint's asset briefs and generated all of
    them; `Provenance` carried three values and recorded one. A differentiator
    with no entry point is not a differentiator.

    Per asset rather than once for the whole run, because the answer genuinely
    differs per asset: a founder has a real dashboard screenshot for the hero and
    nothing at all for the integrations strip. One global choice forces them to
    either fabricate the second or lose the first.

    §8 wants concrete options, so each asset carries the brief in the
    blueprint's own words, the section it lands in, and its prominence — "this
    one will be the largest thing on the page" is answerable; "asset hero-1" is
    not.
    """
    existing = load_plan(run)
    plan = asset_plan(run)

    # A file posted before the gate was answered must survive the plan being
    # re-enumerated, or an upload is silently lost to a retry.
    uploads = {a["id"]: a.get("upload") for a in existing}
    for a in plan:
        a["upload"] = uploads.get(a["id"])

    facts = content_asks(run)

    if not plan and not facts:
        save_plan(run, plan)
        yield Event(Stage.GATE_ASSETS, "done",
                    "no blueprint asked for imagery, and the copy invented nothing")
        return

    decided = {a["id"]: a.get("decision") for a in existing}
    if plan and all(decided.get(a["id"]) for a in plan) and not facts:
        # Already answered — a resumed run must not ask the same question twice.
        save_plan(run, existing)
        yield Event(Stage.GATE_ASSETS, "done",
                    f"{len(plan)} image(s) already decided")
        return

    save_plan(run, plan)
    upload_url = f"/projects/{run.project_id}/assets"
    parts = []
    if plan:
        parts.append(f"{len(plan)} image(s) go on this page — for each one: use "
                     "your own file, have one generated, or leave it out")
    if facts:
        parts.append(f"{len(facts)} line(s) of the copy state something about your "
                     "business that we had to make up — confirm or correct them, "
                     "or leave the draft as it is")

    raise Halt(GateRequest(
        Stage.GATE_ASSETS,
        ". ".join(parts) + ".",
        options=[{
            "kind": "fact",
            "ask_id": f["id"],
            "section_id": f["section_id"],
            "slot": f["slot"],
            "question": f["question"],
            "draft": f["draft"],
            "invented": f["invented"],
            "source_example": f["source_example"],
            "choices": [
                {"choice": "answer",
                 "label": "Give the real answer",
                 "detail": "Used verbatim, and never redrafted afterwards.",
                 "field": "text"},
                {"choice": "keep",
                 "label": "Keep the draft as written"},
            ],
        } for f in facts] + [{
            "kind": "image",
            "asset_id": a["id"],
            "section_id": a["section_id"],
            "brief": a["brief"],
            "prominence": a["prominence"],
            "uploaded": bool(a["upload"]),
            "choices": [
                {"choice": "upload",
                 "label": "Use my own image",
                 "detail": "Restyled to the chosen design direction. Any text it "
                           "gains that the original did not have is rejected.",
                 "post_file_to": f"{upload_url}/{a['id']}"},
                {"choice": "generate",
                 "label": "Generate one from this description"},
                {"choice": "skip",
                 "label": "No image — build the section from type and layout"},
            ],
        } for a in plan],
        artifacts=[],
    ))


def record_asset_decisions(run: Run, decisions: dict[str, str]) -> list[dict]:
    """Write the gate's answer onto the plan. Raises ValueError on a bad answer."""
    plan = load_plan(run)
    known = {a["id"] for a in plan}
    unknown = sorted(set(decisions) - known)
    if unknown:
        raise ValueError(f"no such asset(s): {', '.join(unknown)}")
    for a in plan:
        choice = decisions.get(a["id"], a.get("decision"))
        if choice not in DECISIONS:
            raise ValueError(
                f"{a['id']} needs one of {', '.join(DECISIONS)} — every image is "
                "decided individually, there is no answer for all of them")
        if choice == "upload" and not a.get("upload"):
            raise ValueError(
                f"{a['id']} was answered 'upload' but no file has been posted to "
                f"/projects/{run.project_id}/assets/{a['id']} yet")
        a["decision"] = choice
    save_plan(run, plan)

    # One decision per image, not one for the batch. Provenance downstream is
    # per asset — a founder uploads a real dashboard for the hero and skips the
    # integrations strip — so a single "asset gate answered" line cannot say
    # which of those two produced the file that shipped. The brief is the
    # blueprint's own words, not the user's, so it is safe to quote.
    for a in plan:
        rejected = _note(run, agent="user@gate:assets",
                         summary=f"{a['id']} ({a['section_id']}, "
                                 f"{a['prominence']}): {a['decision']}")
        if rejected:
            telemetry_note(run, "record_asset_decisions", rejected)
            break
    return plan


def record_upload(run: Run, asset_id: str, filename: str, data: bytes) -> dict:
    """Store a user's file against one asset in the plan."""
    plan = load_plan(run)
    entry = next((a for a in plan if a["id"] == asset_id), None)
    if entry is None:
        raise ValueError(f"no such asset {asset_id!r} in this run's plan")
    from PIL import Image, UnidentifiedImageError

    up = run.dir / "uploads"
    up.mkdir(parents=True, exist_ok=True)
    name = f"{asset_id}{Path(filename).suffix.lower() or '.png'}"
    (up / name).write_bytes(data)
    try:
        with Image.open(up / name) as im:
            im.verify()
    except (UnidentifiedImageError, OSError) as e:
        (up / name).unlink(missing_ok=True)
        raise ValueError(f"{filename} is not a readable image: {e}") from e

    entry["upload"] = name
    save_plan(run, plan)
    return entry


def step_assets(run: Run) -> Iterator[Event]:
    """Execute the plan the asset gate decided. One image, one provenance.

    UPLOAD is also the only path carrying anything real about anybody else, so
    it is the only one SCRUBBED — and the scrub runs before the restyle, because
    the restyle is what puts the file in front of a third party.

    UPLOAD is the only path that can ship a claim the user never made, so it is
    the only one gated: the restyle is checked for text fidelity, and a restyle
    that invented words is discarded in favour of the user's untouched original.
    Their real screenshot, unstyled, beats a beautiful one that says something
    about their product that is not true. The rejection is recorded on the asset
    rather than swallowed.
    """
    from sparrow.agents.curator import Curator, derive_variants
    from sparrow.blackboard.schema import Asset, Prominence, Provenance
    from PIL import Image

    bb = _bb(run)
    plan = load_plan(run)
    if not plan:
        # No gate ran: a project created before the asset gate existed, or a
        # blueprint set that asks for no imagery. Generating is what this stage
        # did before the gate, so an old project resumes with its old behaviour
        # rather than stalling on a question nobody was asked.
        plan = [dict(a, decision="generate") for a in asset_plan(run)]
        save_plan(run, plan)

    public = run.workspace / "public" / "assets"
    public.mkdir(parents=True, exist_ok=True)
    cur = Curator()
    made: list[Asset] = []

    for a in plan:
        aid, decision = a["id"], a.get("decision") or "generate"
        if decision == "skip":
            yield Event(Stage.ASSETS, "progress",
                        f"{aid} skipped — the builder composes this section from "
                        "type and layout")
            continue

        path = public / f"{aid}.png"
        rejected: list[str] = []
        scrubbed: list[str] = []

        if decision == "upload":
            original = (run.dir / "uploads" / a["upload"]).read_bytes()
            # FIRST, before any other network call. `restyle` posts the file to
            # a third-party image model and the result is published at the
            # preview URL; a scrub after either is a scrub of a copy.
            scrub = cur.scrub(original)
            scrubbed = list(scrub.changed)
            if scrubbed:
                # Written beside their upload so the substitution is theirs to
                # check. The report says what CATEGORY changed and never the
                # value it changed from — see `curator.Scrub`.
                (run.dir / "uploads" / f"{aid}--scrubbed.png").write_bytes(scrub.image)
                yield Event(Stage.ASSETS, "progress",
                            f"{aid}: real values substituted out of your screenshot "
                            f"before anything else saw it — {', '.join(scrubbed)}")

            restyled = cur.restyle(scrub.image, bb.design_system)
            # Compared SCRUBBED-against-restyled, never original-against-restyled.
            # The gate asks whether the image model invented copy, so the ground
            # truth is what the image model was GIVEN. Against the original,
            # every substitution the scrub made reads as a word the restyle
            # invented, and every legitimate restyle of a dashboard is rejected.
            # The lines come from the scrub, which already read its own output
            # back to verify itself.
            fidelity = cur.check_fidelity(scrub.lines, restyled)
            if fidelity.ok:
                path.write_bytes(restyled)
                provenance = Provenance.RESTYLED
                yield Event(Stage.ASSETS, "progress",
                            f"{aid} restyled from your file — text fidelity holds")
            else:
                # One attempt, no retry. The failure is the model inventing copy,
                # and a second roll of the same prompt is not evidence it will
                # invent less — it is another image call against the same odds.
                # What falls back is the SCRUBBED image, not the upload: the
                # restyle failing is no reason to publish the customer data.
                _write_png(scrub.image, path, Image)
                provenance = Provenance.USER_SUPPLIED
                rejected.append(f"restyle rejected — {fidelity.reason()}")
                yield Event(Stage.ASSETS, "blocked",
                            f"{aid}: restyle invented text ({fidelity.reason()}) — "
                            "shipping your own screenshot instead")
        else:
            path.write_bytes(cur.generate(a["brief"], bb.design_system))
            provenance = Provenance.GENERATED
            scrubbed = []
            yield Event(Stage.ASSETS, "progress", f"{aid} generated")

        with Image.open(path) as im:
            w, h = im.size
        made.append(Asset(
            id=aid, section_id=a["section_id"], brief=a["brief"],
            prominence=Prominence(a["prominence"]), provenance=provenance,
            path=f"assets/{path.name}", width=w, height=h,
            variants={k: f"assets/{v}" for k, v in derive_variants(path).items()},
            rejected=rejected, scrubbed=scrubbed,
        ))

    bb.assets = made
    rejected = _replace(run, "/assets", [a.model_dump(mode="json") for a in made],
                        agent="curator",
                        summary=f"{len(made)} asset(s) produced — "
                                + ", ".join(f"{m.id}:{m.provenance.value}" for m in made))
    if rejected:
        yield Event(Stage.ASSETS, "blocked",
                    f"assets not recorded ({rejected.code}): {rejected.message}")
    tally = {}
    for m in made:
        tally[m.provenance.value] = tally.get(m.provenance.value, 0) + 1
    skipped = sum(1 for a in plan if a.get("decision") == "skip")
    yield Event(Stage.ASSETS, "done",
                f"{len(made)} asset(s)"
                + (" · " + ", ".join(f"{v} {k}" for k, v in sorted(tally.items())) if tally else "")
                + (f" · {skipped} skipped" if skipped else ""))


def _write_png(data: bytes, path: Path, Image) -> None:
    """Normalise whatever the user uploaded to the PNG the workspace expects."""
    import io

    with Image.open(io.BytesIO(data)) as im:
        im.convert("RGB").save(path, "PNG")


def step_build(run: Run) -> Iterator[Event]:
    """Build every section that is not built yet, recording each as it lands.

    RESUME. A section already marked BUILT is skipped rather than rebuilt. That
    is only sound because the status is now written the instant the file is
    written — before this, `status` was `pending` on all nine sections of a
    project whose preview was serving, so skipping on it would have skipped
    nothing and trusting it would have been wrong.

    What that buys, at roughly $0.10-0.25 of builder time per section: a stage
    that died on section six resumes at section six, and `reset_sections` turns
    "just redo the hero" into one section rebuilt rather than the whole page.

    Composition and repair still run on every pass, deliberately. `page.tsx` has
    to name every section including the ones this pass skipped, and a workspace
    that does not build is not a thing to hand to VERIFY — that is what took two
    whole experiments to notice the first time.
    """
    from sparrow.agents.builder import Builder, write_section
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    content = load_content(run)
    blueprints = load_dir(run.dir / "blueprints")
    ws = run.workspace
    primitives = sorted(p.stem for p in (ws / "src/components/ui").glob("*.tsx"))
    builder = Builder()
    built = skipped = 0

    for section in sorted(bb.sections, key=lambda s: s.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None:
            continue
        # BUILT plus a file on disk. The status alone would resume a run whose
        # workspace was rebuilt from the scaffold into composing a page.tsx that
        # imports components no longer there, which fails the build with an error
        # about a missing module and says nothing about why.
        if section.status is BuildStatus.BUILT and (ws / section.target_path).exists():
            skipped += 1
            yield Event(Stage.BUILD, "progress",
                        f"{section.id}: already built — kept")
            continue

        out = builder.build(bb, section, bp, stack=STACK,
                            available_primitives=primitives,
                            assets=bb.assets_for(section.id),
                            asset_base=f"/projects/{run.project_id}/preview",
                            copy=(content.get(section.id) or {}).get("slots"))
        write_section(ws, section, out.code,
                      asset_base=f"/projects/{run.project_id}/preview")
        # Immediately, per section. The file and the record of the file are one
        # transition; anything between them is a window in which a crash leaves
        # the blackboard lying about the workspace.
        rejected = _record_section(run, section.id, agent="builder",
                                   status=BuildStatus.BUILT, bump_attempt=True,
                                   defects=[],
                                   note=f"{len(out.code.splitlines())} loc")
        if rejected:
            yield Event(Stage.BUILD, "blocked",
                        f"{section.id} built but not recorded ({rejected.code}): "
                        f"{rejected.message}")
        built += 1
        yield Event(Stage.BUILD, "progress",
                    f"{section.id}: {len(out.code.splitlines())} loc",
                    cost=out.usage.cost(builder.provider.name, builder.tier))

    from sparrow.cli import _compose_page, _repair_until_builds
    _compose_page(bb, ws)
    run.spent += _repair_until_builds(bb, ws, builder.provider.name)
    yield Event(Stage.BUILD, "done", "page composed and built"
                + (f" · {built} built, {skipped} kept from a previous run"
                   if skipped else ""))


class AssetsNotServed(RuntimeError):
    """The page's own requests 404'd, so nothing rendered on it is real.

    Worth its own type because the response is different from every other
    finding: there is nothing to fix in a section file, and no judgement to
    make about a page that never loaded its stylesheet. A capture taken in
    this state shows Times New Roman on white with every Motion section frozen
    at its initial opacity — and the inspector, honestly, reports collisions
    and faded text. The fixer then reads a source file that is completely
    fine, disputes, and the loop burns all three rounds arguing about a
    screenshot of a page nobody will ever see.

    Measured on a real export after previews moved to Next's `basePath`: 24
    failed requests, no stylesheet, no JS. That was a bug in how the export was
    served (`capture.base_path`), and it cost three paid rounds before anyone
    looked at a crop. `failed_requests` was already being collected and nothing
    read it. This is that check, and it is free.
    """

    def __init__(self, urls: list[str]) -> None:
        self.urls = urls
        super().__init__(
            f"{len(urls)} request(s) failed while loading the page, so it did not "
            "render as a visitor would see it and there is nothing worth "
            "inspecting: " + ", ".join(urls[:5])
            + (f" (+{len(urls) - 5} more)" if len(urls) > 5 else "")
        )


def _inspect_once(run: Run, bb, blueprints, port: int = 4600,
                  disputed: dict[str, list[str]] | None = None):
    """One full look at the built page. Returns (page_findings, per_section, cost).

    Raises `AssetsNotServed` BEFORE the first model call if the page could not
    load its own assets. Everything below this line costs money per section.
    """
    from sparrow.agents.inspector import Inspector, deterministic_defects
    from sparrow.capture import inspect_page, serve

    out = run.workspace / "out"
    if not (out / "index.html").exists():
        raise RuntimeError(
            "no static export at workspace/out — the build did not complete, so "
            "there is nothing to verify. Check the build stage."
        )
    with serve(out, port=port) as url:
        reports = inspect_page(url, run.dir / "shots" / "sections")

    failed = sorted({u for r in reports.values() for u in r.failed_requests})
    if failed:
        raise AssetsNotServed(failed)

    page_level = deterministic_defects(reports)

    by_index: dict[int, list] = {}
    for r in reports.values():
        for sh in r.sections:
            by_index.setdefault(sh.section_index, []).append(sh)

    inspector = Inspector()
    ordered = sorted(bb.sections, key=lambda s: s.order)
    per_section: dict[str, list] = {}
    cost = 0.0
    for pos, idx in enumerate(sorted(by_index)):
        if pos >= len(ordered):
            break
        sec = ordered[pos]
        defects, usage = inspector.inspect_section(
            bb, sec, by_index[idx], page_level, blueprints.get(sec.blueprint_id),
            (disputed or {}).get(sec.id))
        cost += usage.cost(inspector.provider.name, inspector.tier)
        if defects:
            per_section[sec.id] = defects
    return page_level, per_section, cost


def _drift_defects(findings: list, bb: Blackboard) -> dict[str, list]:
    """Group audit findings by the section whose file they were measured in.

    `audit.Finding` and inspector `Defect` are deliberately different shapes —
    one is a line in a file, the other is something seen in a browser — so this
    adapts rather than pretending they are one type. What has to survive the
    adaptation is what `Fixer.fix` actually reads (`severity`, `what`, `where`)
    plus `source`, which is how a person reading the log tells a measured
    finding from a judged one.

    Severity is one value for every category, not a ranking. Drift is a
    consistency violation, never a rendering break, and deciding that an
    off-scale radius outranks an off-scale gap would be exactly the unmeasured
    preference §6 rejects. The fixer is told what is wrong and what the scale
    permits; it is not told which drift to care about most.

    The permitted set travels WITH the finding, quoted from the same
    `DesignSystem` the audit derived it from. Without it the fixer knows only
    that gap-7 is wrong, and a fixer guessing at the remedy replaces one
    off-scale value with another.
    """
    from sparrow.agents.inspector import Defect
    from sparrow.audit import permitted

    owner = {Path(s.target_path).name: s.id for s in bb.sections}
    allow = permitted(bb.design_system)
    out: dict[str, list] = {}
    for f in findings:
        sid = owner.get(f.file)
        if sid is None:
            # A .tsx no section owns. It is still reported in the count at the
            # gate; there is simply no section to route a fix to.
            continue
        what = f"{f.category}: {f.detail}"
        ok = allow.get(f.category)
        if ok:
            what += f" — the design system declares only {', '.join(sorted(ok))}"
        out.setdefault(sid, []).append(Defect(
            severity="medium", code=f.category, what=what,
            where=f"{f.file}:{f.line}", source="computed",
        ))
    return out


def _settle_sections(run: Run, bb: Blackboard, findings: list,
                     per_section: dict[str, list],
                     disputed: dict[str, list[str]]) -> Iterator[Event]:
    """Write the last look's verdict onto every section that was built.

    Both halves count. Drift is measured from the code and visual defects are
    seen in a browser, and a section carrying either is not clean — the gate
    question already reports both, and a `status` that disagreed with the
    sentence next to it would be worse than no status.

    PENDING sections are left alone. A section with no blueprint is never built
    and never inspected, and marking it BUILT here because the inspector had
    nothing to say about it would invent a build that did not happen — which is
    the same class of lie, pointing the other way, as the one this work fixes.
    """
    remaining = _drift_defects(findings, bb)
    for sid, ds in per_section.items():
        remaining.setdefault(sid, []).extend(ds)

    for section in bb.sections:
        if section.status is BuildStatus.PENDING:
            continue
        ds = remaining.get(section.id, [])
        note = ""
        if not ds and disputed.get(section.id):
            # Clean, but only after the fixer refused some of what it was shown.
            # Worth a line: the difference between "nothing was wrong" and
            # "something was reported and argued down" is the whole diagnosis.
            note = f"clean, {len(disputed[section.id])} defect(s) disputed"
        rejected = _record_section(
            run, section.id, agent="observer",
            status=BuildStatus.DEFECTIVE if ds else BuildStatus.BUILT,
            defects=[f"{d.source}:{d.code} {d.what}" for d in ds], note=note)
        if rejected:
            yield Event(Stage.VERIFY, "blocked",
                        f"{section.id} verdict not recorded ({rejected.code}): "
                        f"{rejected.message}")


def step_verify(run: Run) -> Iterator[Event]:
    """Look, fix, look again — until the page is clean or the budget is spent.

    Until now this stage inspected the page, counted the defects, and threw them
    away: `total += len(defects)` and nothing more. Gate 3 then asked "ship it?"
    while holding a list of problems nothing could act on, and the harness was
    paying about $1.20 a run for findings it discarded.

    That is the missing half of CLAUDE.md §6's build → look → fix loop. Capped at
    3 like every other loop, because critic-refine plateaus at two or three
    iterations and then starts inventing objections to justify itself.

    The DRIFT half stayed discarded after the visual half was wired up.
    `audit_dir` ran at the top of every round and its findings reached the
    progress line and the gate question — but only `per_section` was passed to
    the fixer, so nothing ever acted on them. A real run reported 31
    off-scale-gap findings in round one, again in round two, and again at the
    gate, and fixed none of them. Drift now goes to the fixer alongside what the
    inspector saw, in ONE call per section: two calls would have the second
    fixing code the first had already rewritten.
    """
    from sparrow.agents.builder import Fixer, write_section
    from sparrow.audit import audit_dir, summarise
    from sparrow.blueprints import load_dir
    from sparrow.cli import _run_build
    from sparrow.loop import Blocked, Outcome, Rounds

    bb = _bb(run)
    blueprints = load_dir(run.dir / "blueprints")
    rounds = Rounds("verify", cap=3)
    fixer: Fixer | None = None
    unserved: list[str] = []
    # A disputed defect must not come back next round. Without this the inspector
    # re-reports it, the fixer disputes it again, and the loop spends its whole
    # budget on one thing nobody is going to change.
    disputed: dict[str, list[str]] = {}
    port = 4600

    while True:
        findings = audit_dir(run.workspace / "src/components/sections", bb.design_system)
        try:
            page_level, per_section, cost = _inspect_once(run, bb, blueprints, port,
                                                          disputed)
        except AssetsNotServed as e:
            # Stop the round before the inspector is asked anything. Nothing in a
            # section file explains a 404, so every model call this round would
            # buy an opinion about a page that never loaded.
            yield Event(Stage.VERIFY, "blocked",
                        f"the preview is not serving its own assets — {e}")
            unserved = e.urls
            break
        port += 1                       # a fresh port each pass; the last may still be closing

        # Drift is NOT suppressed by `disputed` the way a visual defect is.
        # There is nothing to dispute about arithmetic against a closed scale,
        # so it is recomputed from the code every round and stays on the list
        # until the code stops drifting.
        drift = _drift_defects(findings, bb)
        work: dict[str, list] = {}
        for sid in (*drift, *per_section):
            # Drift first: it names a file and a line, which orients the fixer
            # before it reads a description of something merely seen.
            work.setdefault(sid, [*drift.get(sid, []), *per_section.get(sid, [])])

        remaining = sum(len(v) for v in per_section.values())
        yield Event(Stage.VERIFY, "progress",
                    f"{summarise(findings).splitlines()[0]} · "
                    f"{len(page_level)} computed · {remaining} visual", cost=cost)

        if not work:
            rounds.complete("audit clean and no visual defects")
            break

        slot = rounds.reserve()
        if isinstance(slot, Blocked):
            yield Event(Stage.VERIFY, "blocked", f"{slot.code}: {slot.message}")
            break

        # Recorded BEFORE the first fixer call of the round. The fixer is the
        # part that can throw, time out, or be killed; a defect list that only
        # lands after it returns is a defect list that is absent exactly when
        # someone needs to know what the run was working on when it died.
        # `_record_section` writes nothing when nothing moved, so a second round
        # that finds the same defects does not churn the version.
        for sid, defects in work.items():
            rejected = _record_section(
                run, sid, agent="inspector", status=BuildStatus.DEFECTIVE,
                defects=[f"{d.source}:{d.code} {d.what}" for d in defects])
            if rejected:
                yield Event(Stage.VERIFY, "blocked",
                            f"{sid} defects not recorded ({rejected.code}): "
                            f"{rejected.message}")

        fixer = fixer or Fixer()
        fixed_any = False
        # Every file this round is about to overwrite, as it stood before the
        # overwrite. This is what a failed rebuild is restored from.
        snapshots: dict[Path, str] = {}
        for sid, defects in work.items():
            section = next(s for s in bb.sections if s.id == sid)
            path = run.workspace / section.target_path
            before = path.read_text()
            try:
                out, dispute = fixer.fix(bb, section, before, defects)
            except Exception as e:
                yield Event(Stage.VERIFY, "blocked", f"{sid}: fixer failed — {e}")
                continue
            if dispute:
                disputed.setdefault(sid, []).append(dispute)
                # THE reason this stage got a writer. A dispute changes no field
                # on the blackboard, suppresses the defect for every later round,
                # and until now lived only in the `disputed` dict above — which
                # dies with the process. One run spent three rounds and ~$2 on
                # four disputes and afterwards there was nothing on disk saying
                # what had been disputed, so nothing to diagnose. It is the
                # fixer's own prose about a section file, not user material.
                rejected = _note(run, agent="fixer",
                                 summary=f"{sid}: DISPUTED — {dispute}")
                if rejected:
                    yield Event(Stage.VERIFY, "blocked",
                                f"{sid} dispute not recorded ({rejected.code}): "
                                f"{rejected.message}")
                yield Event(Stage.VERIFY, "progress", f"{sid}: disputed — {dispute[:70]}")
                continue
            snapshots.setdefault(path, before)
            write_section(run.workspace, section, out.code,
                          asset_base=f"/projects/{run.project_id}/preview")
            # Status stays DEFECTIVE. The file changed; nothing has looked at the
            # result yet, and loop.py's fourth rule is that nothing is marked done
            # on an agent's say-so. The next round's inspection is the evidence,
            # and the settle at the end of the stage is where it is applied.
            rejected = _record_section(
                run, sid, agent="fixer", bump_attempt=True,
                note="fix applied for " + ", ".join(sorted({d.code for d in defects})))
            if rejected:
                yield Event(Stage.VERIFY, "blocked",
                            f"{sid} fix not recorded ({rejected.code}): "
                            f"{rejected.message}")
            fixed_any = True
            yield Event(Stage.VERIFY, "progress",
                        f"{sid}: fixed {len(defects)} defect(s)",
                        cost=out.usage.cost(fixer.provider.name, fixer.tier))

        if not fixed_any:
            # Every defect was disputed, so another pass would look at the same
            # page and find the same things. Stop rather than burn the budget.
            rounds.settle(Outcome.SUPERSEDED, "all defects disputed")
            yield Event(Stage.VERIFY, "progress",
                        "nothing changed — every defect was disputed")
            break

        rounds.settle(Outcome.ATTEMPTED,
                      f"fixed {sum(len(v) for v in work.values())} defect(s)")
        ok, output = _run_build(run.workspace)
        if not ok:
            # This branch used to emit "reverting to the last good export" and
            # break, having restored nothing. The workspace was left holding the
            # code that had just failed to build, behind a message claiming
            # recovery — one project sat unbuildable for hours that way. The
            # sentence is now the thing that happens.
            reverted = []
            for target, original in snapshots.items():
                target.write_text(original)
                sid = next((x.id for x in bb.sections
                            if run.workspace / x.target_path == target), None)
                if sid:
                    reverted.append(sid)
                    _record_section(run, sid, agent="orchestrator",
                                    status=BuildStatus.DEFECTIVE,
                                    note="fix reverted — it did not build")
            recovered, again = _run_build(run.workspace)
            if not recovered:
                # Nothing further in this stage can help, and gate 3 must not
                # ask a human to ship a workspace that does not compile.
                raise RuntimeError(
                    "a fix broke the build and restoring the previous section "
                    "code did not recover it — the workspace does not build. "
                    "This needs a look, not another round.\n"
                    + again.strip()[-1200:]
                )
            yield Event(Stage.VERIFY, "blocked",
                        f"a fix broke the build — reverted {len(snapshots)} "
                        "section(s) to the last code that built, and rebuilt")
            break
        yield Event(Stage.VERIFY, "progress", f"rebuilt · {rounds.summary()}")

    findings = audit_dir(run.workspace / "src/components/sections", bb.design_system)
    looked = True
    try:
        _, per_section, _ = _inspect_once(run, bb, blueprints, port + 10, disputed)
        left = sum(len(v) for v in per_section.values())
    except AssetsNotServed as e:
        per_section, left, unserved, looked = {}, 0, e.urls, False

    # One settle, on the evidence of the last look. A section is BUILT again only
    # because something measured it clean — never because a fix was written and
    # assumed to have worked. If the final look never happened (the page could
    # not serve its own files) nothing is settled at all: the alternative is
    # marking every section clean on the strength of an inspection that returned
    # no defects because it never ran.
    if looked:
        for ev in _settle_sections(run, bb, findings, per_section, disputed):
            yield ev

    # A page that cannot load its own assets is not a page anyone should be asked
    # to ship, so that leads the question rather than sitting in a log line.
    headline = (
        f"The preview is not serving {len(unserved)} of its own files, so what "
        "you see is unstyled and is not what was built. This needs fixing before "
        "it can be judged. "
        if unserved else "The site is built. "
    )
    raise Halt(GateRequest(
        Stage.GATE_PREVIEW,
        headline
        + f"{len(findings)} drift finding(s), {left} visual defect(s)"
        + (f", {sum(len(v) for v in disputed.values())} disputed" if disputed else "")
        + f". {rounds.summary()}. Ship it?",
        options=[{"choice": "approve", "label": "Looks good — publish"},
                 {"choice": "revise", "label": "Send it back with a note",
                  "needs_note": True}],
        artifacts=[str(run.workspace / "out")],
    ))


def make_workspace(run: Run, scaffold: Path) -> None:
    """Copy the scaffold and bind it to the path the preview serves from.

    Rewriting root-absolute URLs in the served HTML is not enough for a Next app.
    Its RSC payload carries "/_next/static/chunks/..." inside JSON strings, and
    its client runtime builds more paths at runtime — none of which an HTML
    rewrite can reach. The scripts then load but the module registry does not
    match, hydration fails silently with no console error and no 404, and every
    element stays frozen at its `initial` opacity. Which is what "the page is
    invisible and there is no animation" turned out to be.

    basePath makes Next generate correct URLs everywhere itself. The export is
    then bound to this project's preview path, which is what a preview is for.
    """
    ws = run.workspace
    ws.mkdir(parents=True, exist_ok=True)
    shutil.copytree(scaffold, ws, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", ".next", "out", "README.md"))
    cfg = ws / "next.config.ts"
    base = f"/projects/{run.project_id}/preview"
    cfg.write_text(cfg.read_text().replace(
        "  trailingSlash: true,",
        f'  trailingSlash: true,\n\n'
        f'  // Bound to the preview path so Next generates correct URLs in the\n'
        f'  // HTML, the RSC payload and at runtime. Without it hydration fails\n'
        f'  // silently and nothing animates.\n'
        f'  basePath: "{base}",\n'
        f'  assetPrefix: "{base}",'))
    subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=ws, check=True,
                   capture_output=True)

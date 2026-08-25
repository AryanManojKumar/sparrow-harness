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

from sparrow.blackboard.schema import Blackboard, Ground, Section
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


def _save(run: Run, bb: Blackboard) -> None:
    bb.version += 1
    run.blackboard_path.write_text(bb.model_dump_json(indent=2))


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
    _save(run, bb)
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
    bb.design_system = DesignSystem.model_validate(proposals[index]["design_system"])
    _save(run, bb)
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

def step_assets(run: Run) -> Iterator[Event]:
    from sparrow.agents.curator import Curator, derive_variants
    from sparrow.blackboard.schema import Asset, Prominence, Provenance
    from sparrow.blueprints import load_dir
    from PIL import Image

    bb = _bb(run)
    blueprints = load_dir(run.dir / "blueprints")
    public = run.workspace / "public" / "assets"
    public.mkdir(parents=True, exist_ok=True)
    cur = Curator()
    made: list[Asset] = []

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
            aid = f"{section.id}-{i}"
            path = public / f"{aid}.png"
            path.write_bytes(cur.generate(brief, bb.design_system))
            with Image.open(path) as im:
                w, h = im.size
            prom = (Prominence.DOMINANT if len(bp.assets) == 1
                    else Prominence.SUPPORTING if i == 1 else Prominence.THUMBNAIL)
            made.append(Asset(
                id=aid, section_id=section.id, brief=brief, prominence=prom,
                provenance=Provenance.GENERATED, path=f"assets/{path.name}",
                width=w, height=h,
                variants={k: f"assets/{v}" for k, v in derive_variants(path).items()},
            ))
            yield Event(Stage.ASSETS, "progress", f"{aid} [{prom.value}]")

    bb.assets = made
    _save(run, bb)
    yield Event(Stage.ASSETS, "done", f"{len(made)} asset(s)")


def step_build(run: Run) -> Iterator[Event]:
    from sparrow.agents.builder import Builder, write_section
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    blueprints = load_dir(run.dir / "blueprints")
    ws = run.workspace
    primitives = sorted(p.stem for p in (ws / "src/components/ui").glob("*.tsx"))
    builder = Builder()

    for section in sorted(bb.sections, key=lambda s: s.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None:
            continue
        out = builder.build(bb, section, bp, stack=STACK,
                            available_primitives=primitives,
                            assets=bb.assets_for(section.id),
                            asset_base=f"/projects/{run.project_id}/preview")
        write_section(ws, section, out.code)
        yield Event(Stage.BUILD, "progress",
                    f"{section.id}: {len(out.code.splitlines())} loc",
                    cost=out.usage.cost(builder.provider.name, builder.tier))

    from sparrow.cli import _compose_page, _repair_until_builds
    _compose_page(bb, ws)
    run.spent += _repair_until_builds(bb, ws, builder.provider.name)
    yield Event(Stage.BUILD, "done", "page composed and built")


def _inspect_once(run: Run, bb, blueprints, port: int = 4600,
                  disputed: dict[str, list[str]] | None = None):
    """One full look at the built page. Returns (page_findings, per_section, cost)."""
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
    # A disputed defect must not come back next round. Without this the inspector
    # re-reports it, the fixer disputes it again, and the loop spends its whole
    # budget on one thing nobody is going to change.
    disputed: dict[str, list[str]] = {}
    port = 4600

    while True:
        findings = audit_dir(run.workspace / "src/components/sections", bb.design_system)
        page_level, per_section, cost = _inspect_once(run, bb, blueprints, port,
                                                       disputed)
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
                yield Event(Stage.VERIFY, "progress", f"{sid}: disputed — {dispute[:70]}")
                continue
            snapshots.setdefault(path, before)
            write_section(run.workspace, section, out.code)
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
            for target, original in snapshots.items():
                target.write_text(original)
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
    _, per_section, _ = _inspect_once(run, bb, blueprints, port + 10, disputed)
    left = sum(len(v) for v in per_section.values())

    raise Halt(GateRequest(
        Stage.GATE_PREVIEW,
        f"The site is built. {len(findings)} drift finding(s), {left} visual defect(s)"
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

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
                # Chrome sits on the page ground; content alternates beneath it.
                ground=Ground.PAGE if t in CHROME else
                       (Ground.PAGE if content.index(t) % 2 == 0 else Ground.MUTED))
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
    raise Halt(GateRequest(
        Stage.GATE_DESIGN,
        "Which direction should the site take?",
        options=[{k: p[k] for k in ("index", "signature", "atmosphere", "type")}
                 for p in proposals],
        artifacts=[str(run.dir / "directions.json")],
    ))


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
                            assets=bb.assets_for(section.id))
        write_section(ws, section, out.code)
        yield Event(Stage.BUILD, "progress",
                    f"{section.id}: {len(out.code.splitlines())} loc",
                    cost=out.usage.cost(builder.provider.name, builder.tier))

    from sparrow.cli import _compose_page, _repair_until_builds
    _compose_page(bb, ws)
    run.spent += _repair_until_builds(bb, ws, builder.provider.name)
    yield Event(Stage.BUILD, "done", "page composed and built")


def step_verify(run: Run) -> Iterator[Event]:
    from sparrow.agents.inspector import Inspector, deterministic_defects
    from sparrow.audit import audit_dir, summarise
    from sparrow.blueprints import load_dir
    from sparrow.capture import inspect_page, serve

    bb = _bb(run)
    out = run.workspace / "out"
    if not (out / "index.html").exists():
        # The first real run reported "0 drift findings, 0 visual defects" against
        # an export that did not exist: inspect_page served an empty directory,
        # found no sections, and every check passed vacuously. A verification that
        # cannot fail is worse than none.
        raise RuntimeError(
            "no static export at workspace/out — the build did not complete, so "
            "there is nothing to verify. Check the build stage."
        )
    findings = audit_dir(run.workspace / "src/components/sections", bb.design_system)
    yield Event(Stage.VERIFY, "progress", summarise(findings).splitlines()[0])

    blueprints = load_dir(run.dir / "blueprints")
    with serve(out, port=4600) as url:
        reports = inspect_page(url, run.dir / "shots" / "sections")
    page_level = deterministic_defects(reports)
    yield Event(Stage.VERIFY, "progress",
                f"deterministic: {len(page_level)} finding(s), 0 model calls")

    by_index: dict[int, list] = {}
    for r in reports.values():
        for s in r.sections:
            by_index.setdefault(s.section_index, []).append(s)

    inspector = Inspector()
    ordered = sorted(bb.sections, key=lambda s: s.order)
    total = 0
    for pos, idx in enumerate(sorted(by_index)):
        if pos >= len(ordered):
            break
        sec = ordered[pos]
        defects, usage = inspector.inspect_section(
            bb, sec, by_index[idx], page_level, blueprints.get(sec.blueprint_id))
        total += len(defects)
        yield Event(Stage.VERIFY, "progress",
                    f"{sec.id}: {len(defects) or 'no'} defect(s)",
                    cost=usage.cost(inspector.provider.name, inspector.tier))

    raise Halt(GateRequest(
        Stage.GATE_PREVIEW,
        f"The site is built. {len(findings)} drift finding(s), {total} visual defect(s). Ship it?",
        options=[{"choice": "approve", "label": "Looks good — publish"},
                 {"choice": "revise", "label": "Send the defects back to be fixed"}],
        artifacts=[str(run.workspace / "out")],
    ))


def make_workspace(run: Run, scaffold: Path) -> None:
    ws = run.workspace
    ws.mkdir(parents=True, exist_ok=True)
    shutil.copytree(scaffold, ws, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", ".next", "out", "README.md"))
    subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=ws, check=True,
                   capture_output=True)

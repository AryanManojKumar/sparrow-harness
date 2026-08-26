"""sparrow — command line entry point.

Deliberately thin. The loop lives in the modules; this only wires them together
so the whole thing can be exercised without an HTTP layer. FastAPI arrives when
there is a UI to serve, not before.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from sparrow.audit import audit_dir, summarise
from sparrow.blackboard.schema import Blackboard
from sparrow.render.tokens import apply_to_stylesheet, font_imports, to_prompt

ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = ROOT / "scaffold"
PROJECTS = ROOT / "projects"


def _workspace(project: str) -> Path:
    return PROJECTS / project / "workspace"


def cmd_new(args) -> int:
    ws = _workspace(args.project)
    if ws.exists() and any(ws.iterdir()):
        print(f"refusing to overwrite existing workspace at {ws}", file=sys.stderr)
        return 1
    ws.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        SCAFFOLD, ws, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("node_modules", ".next", "out", "README.md"),
    )
    print(f"workspace  {ws}")
    print("installing dependencies (hardlinked from the pnpm store) …")
    subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=ws, check=True)
    print("ready")
    return 0


def cmd_tokens(args) -> int:
    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    if bb.design_system is None:
        print("no design_system on the blackboard", file=sys.stderr)
        return 1
    ws = _workspace(bb.project_id)
    css = ws / "src/app/globals.css"
    css.write_text(apply_to_stylesheet(css.read_text(), bb.design_system))
    print(f"tokens written to {css}")

    # Bind the chosen families, so `font-display` / `font-body` / `font-mono`
    # actually resolve for the builder.
    imp, consts, rest = font_imports(bb.design_system)
    cls, theme = rest.split("|||")
    layout = ws / "src/app/layout.tsx"
    src = layout.read_text()
    src = re.sub(r'import \{[^}]*\} from "next/font/google";\n', "", src)
    src = re.sub(r"const \w+ = \w+\(\s*\{\s*subsets.*?\}\s*\);\n", "", src, flags=re.S)
    src = src.replace('import "./globals.css";', f'import "./globals.css";\n{imp}\n{consts}')
    src = re.sub(r'\{/\* families are bound.*?\*/\}\n\s*', "", src)
    src = re.sub(r'<html lang="en"[^>]*>',
                 f'<html lang="en" className={{cn("font-body", `{cls}`)}}>', src)
    layout.write_text(src)

    # Bind the utilities in @theme so Tailwind emits font-display/-body/-mono.
    css_src = css.read_text()
    css_src = re.sub(r"\n *--font-(display|body|mono): [^;]+;", "", css_src)
    css_src = css_src.replace("@theme inline {", f"@theme inline {{\n{theme}")
    css.write_text(css_src)
    print(f"fonts bound in {layout.name}: {bb.design_system.font_display} / "
          f"{bb.design_system.font_body}"
          + (f" / {bb.design_system.font_mono}" if bb.design_system.font_mono else ""))
    return 0


def cmd_prompt(args) -> int:
    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    if bb.design_system is None:
        print("no design_system on the blackboard", file=sys.stderr)
        return 1
    print(to_prompt(bb.design_system))
    return 0


def cmd_audit(args) -> int:
    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    if bb.design_system is None:
        print("no design_system on the blackboard", file=sys.stderr)
        return 1
    sections = Path(args.sections or _workspace(bb.project_id) / "src/components/sections")
    findings = audit_dir(sections, bb.design_system)
    print(summarise(findings))
    return 1 if findings else 0


def cmd_build(args) -> int:
    """Run the builder over every pending section. One call each, blind to the rest."""
    from sparrow.agents.builder import Builder, write_section
    from sparrow.blackboard.store import Store
    from sparrow.blueprints import load_dir

    store = Store(Path(args.blackboard))
    bb = store.load()
    if bb.design_system is None:
        print("no design_system on the blackboard", file=sys.stderr)
        return 1

    blueprints = load_dir(Path(args.blueprints))
    ws = _workspace(bb.project_id)
    primitives = sorted(p.stem for p in (ws / "src/components/ui").glob("*.tsx"))
    stack = (
        "Next.js 16 App Router, static export. React 19. TypeScript. Tailwind v4. "
        "Motion 13 — import from 'motion/react', NEVER 'framer-motion'. "
        "Icons from 'lucide-react'. A section that animates must be a client "
        'component ("use client").'
    )

    builder = Builder()
    total = 0.0
    print(f"provider {builder.provider.name} · tier {builder.tier.value}\n")

    for section in sorted(bb.sections, key=lambda s: s.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None:
            print(f"  {section.id}: no blueprint {section.blueprint_id!r}", file=sys.stderr)
            return 1
        out = builder.build(bb, section, bp, stack=stack, available_primitives=primitives,
                            assets=bb.assets_for(section.id))
        path = write_section(ws, section, out.code)
        cost = out.usage.cost(builder.provider.name, builder.tier)
        total += cost
        loc = len(out.code.splitlines())
        saved = out.usage.uncached_cost(builder.provider.name, builder.tier) - cost
        cache = (f"  cache {out.usage.cache_hit_rate:>4.0%} (-${saved:.4f})"
                 if out.usage.cached_tokens else "  cache   0%")
        print(f"  {section.order}. {section.id:14} {loc:>4} loc  "
              f"{out.usage.total_input:>6,} in  {out.usage.output_tokens:>6,} out  "
              f"${cost:.4f}{cache}")
        if out.extension_request:
            print(f"     ↳ EXTENSION REQUEST: {out.extension_request}")

    _compose_page(bb, ws)
    total += _repair_until_builds(bb, ws, builder.provider.name)
    print(f"\n  total ${total:.4f}")
    return 0


_FAILED_FILE = re.compile(r"\./(src/components/sections/\w+\.tsx)")


def _compose_page(bb, ws: Path) -> None:
    """Assemble the built sections into the page, in sitemap order.

    Nobody owned this. The builder writes section files and stops; without a
    composer the scaffold's placeholder page ships and every section is dead
    code that still compiles. drift-test-03 got all the way to a screenshot
    before that surfaced.
    """
    ordered = sorted(bb.sections, key=lambda s: s.order)
    imports = "\n".join(
        f'import {s.component_name} from "@/components/sections/{s.component_name}";'
        for s in ordered
    )
    body = "\n".join(f"      <{s.component_name} />" for s in ordered)
    (ws / "src/app/page.tsx").write_text(
        f"{imports}\n\nexport default function Home() {{\n"
        f"  return (\n    <main>\n{body}\n    </main>\n  );\n}}\n"
    )

    # Placeholder metadata so the page is not shipped titleless; content_editor
    # owns the real copy once it exists.
    layout = ws / "src/app/layout.tsx"
    src = layout.read_text()
    if bb.brief and 'title: ""' in src:
        offer = bb.brief.offering.split(".")[0][:52]
        src = src.replace('title: ""', f'title: "{offer}"')
        src = src.replace('description: ""', f'description: "{bb.brief.offering[:150]}"')
        layout.write_text(src)
    print(f"\n  composed page.tsx — {len(ordered)} sections in sitemap order")


def _run_build(ws: Path) -> tuple[bool, str]:
    r = subprocess.run(["pnpm", "build"], cwd=ws, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


def _repair_until_builds(bb, ws: Path, provider_name: str, max_attempts: int = 3) -> float:
    """Build, and if it fails, hand the error back to the repairer.

    Capped at 3 — the same cap as every other loop in the harness. A build that
    still fails after three attempts is an escalation, not a retry.
    """
    from sparrow.agents.builder import Repairer, write_section

    from sparrow.loop import Blocked, Outcome, Rounds

    spent = 0.0
    repairer: Repairer | None = None
    rounds = Rounds("build", cap=max_attempts)

    while True:
        ok, output = _run_build(ws)
        if ok:
            rounds.complete("pnpm build exited 0")
            print(f"\n  build ok — {rounds.summary()}")
            return spent

        slot = rounds.reserve()
        if isinstance(slot, Blocked):
            print(f"\n  {slot.code}: {slot.message}", file=sys.stderr)
            return spent

        m = _FAILED_FILE.search(output)
        if not m:
            # Not an attempt at the problem — the problem was never identified.
            rounds.settle(Outcome.SUPERSEDED, "no section could be blamed")
            print(f"\n  build failed, and no section could be blamed:\n{output[-800:]}",
                  file=sys.stderr)
            return spent

        rel = m.group(1)
        section = next((s for s in bb.sections if s.target_path == rel), None)
        if section is None:
            rounds.settle(Outcome.SUPERSEDED, f"{rel} is not a known section")
            print(f"\n  build failed in {rel}, which is not a known section", file=sys.stderr)
            return spent

        first = output.find("Export ")
        err = output[max(0, first - 200):][:2500] if first > 0 else output[-2500:]
        print(f"\n  build failed in {section.id} — repairing "
              f"(round {slot}/{max_attempts})")

        repairer = repairer or Repairer()
        try:
            out = repairer.repair(bb, section, (ws / rel).read_text(), err)
        except Exception as e:
            # Transport or parse failure is not an attempt at the defect.
            rounds.settle(Outcome.INFRA_FAILED, f"{type(e).__name__}: {e}")
            print(f"     repairer failed to respond ({type(e).__name__}) — "
                  f"not charged, {rounds.remaining} left", file=sys.stderr)
            continue

        write_section(ws, section, out.code)
        rounds.settle(Outcome.ATTEMPTED, f"repaired {section.id}")
        cost = out.usage.cost(provider_name, repairer.tier)
        spent += cost
        print(f"     repaired  {out.usage.input_tokens:,} in  "
              f"{out.usage.output_tokens:,} out  ${cost:.4f}")


def cmd_serve(args) -> int:
    """Run the HTTP API. The frontend drives everything through this."""
    import uvicorn
    print(f"sparrow api on http://{args.host}:{args.port}  (docs at /docs)")
    uvicorn.run("sparrow.api:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_run(args) -> int:
    """Drive a project through the pipeline, stopping at each gate."""
    import json as _json

    from sparrow.orchestrator import Run, Stage
    from sparrow import steps as _steps

    urls_file = PROJECTS / args.project / "urls.json"
    urls = _json.loads(urls_file.read_text()) if urls_file.exists() else args.url
    run = Run(args.project, ROOT, {
        Stage.BRIEF: _steps.step_brief,
        Stage.SOURCES: lambda r: _steps.step_sources(r, urls),
        Stage.DESIGN: _steps.step_design,
        Stage.CONTENT: _steps.step_content,
        Stage.GATE_ASSETS: _steps.step_asset_gate,
        Stage.ASSETS: _steps.step_assets,
        Stage.BUILD: _steps.step_build,
        Stage.VERIFY: _steps.step_verify,
    })
    while True:
        for ev in run.advance():
            print(ev.line())
        if run.pending is None:
            break
        r = run.pending
        print(f"\n  ── {r.gate.value} ──\n  {r.question}")
        for o in r.options:
            if "asset_id" in o:          # the asset gate lists images, not choices
                print(f"    {o['asset_id']:<22} [{o['prominence']:<10}] "
                      f"{o['brief'][:60]}")
                continue
            print(f"    [{o.get('index', o.get('choice'))}] "
                  f"{o.get('signature') or o.get('label')}")
        if args.yes and r.gate is Stage.GATE_DESIGN:
            print("  --yes: taking direction 0")
            _steps.adopt_direction(run, 0)
            run.resolve({"choice": 0})
        elif args.yes and r.gate is Stage.GATE_ASSETS:
            # Unattended, so there is nobody to hand over a file. Generating is
            # the only choice that can be made without a human, and it is stated
            # rather than defaulted to: the whole point of this gate is that
            # generated imagery should be a decision, not what happens by
            # itself. An interactive run answers it properly.
            plan = _steps.record_asset_decisions(
                run, {a["asset_id"]: "generate" for a in r.options})
            print(f"  --yes: generating all {len(plan)} image(s) — no upload possible "
                  "unattended")
            run.resolve({"assets": {a["id"]: a["decision"] for a in plan}})
        elif args.yes:
            run.resolve({"choice": "approve"})
        else:
            print("\n  answer with: sparrow gate {p} <choice>".format(p=args.project))
            return 0
    print(f"\n  done · ${run.spent:.4f}")
    return 0


def cmd_scout(args) -> int:
    """Extract reference sites, rank them against the brief, emit the design brief."""
    from sparrow.blueprints import Blueprint  # noqa: F401  (keeps import graph honest)
    from sparrow.providers import Tier, get_provider
    from sparrow.rank import (Candidate, RANKABLE, commonality, pick_primary,
                              rank_section, register_report, to_design_brief)
    from sparrow.scout import classify, extract

    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    if bb.brief is None:
        print("no brief on the blackboard", file=sys.stderr)
        return 1

    out_dir = PROJECTS / bb.project_id / "sources"
    provider = get_provider()
    labelled: dict[str, list[tuple[str, int]]] = {}
    by_type: dict[str, list[Candidate]] = {}
    registers: dict[str, object] = {}
    spent = 0.0

    for url in args.urls:
        site = url.split("//")[-1].split("/")[0]
        r = extract(url, out_dir, shots=args.shots)
        if not r.ok:
            print(f"  {site:26} could not be read — {r.error[:50]}", file=sys.stderr)
            continue
        if len(r.bands) < 4:
            print(f"  {site:26} only {len(r.bands)} section(s) — too thin to rank, skipped",
                  file=sys.stderr)
            continue
        if r.register is not None:
            registers[site] = r.register
        types = classify(provider, r.bands)
        labelled[site] = [(t, b.index + 1) for t, b in zip(types, r.bands)]
        for t, b in zip(types, r.bands):
            if t in RANKABLE:
                by_type.setdefault(t, []).append(Candidate(
                    site=site, section_type=t, position=b.index + 1, height=b.height,
                    words=b.words, images=b.images, buttons=b.buttons,
                    list_items=b.listItems, headings=b.headings, text=b.text,
                    unrendered=b.unrendered,
                ))
        print(f"  {site:26} {len(r.bands):>2} sections  {', '.join(dict.fromkeys(types))[:64]}")

    if len(labelled) < 2:
        print("\nneed at least two readable sources to rank", file=sys.stderr)
        return 1

    comm = commonality(labelled)
    print(f"\n{comm.report()}")

    primary, why, usage = pick_primary(provider, bb.brief, labelled)
    spent += usage.cost(provider.name, Tier.CHEAP)
    print(f"\nprimary reference: {primary}\n  {why}")

    rankings: dict[str, dict] = {}
    for t in comm.typical_order:
        cands = by_type.get(t, [])
        if not cands:
            continue
        r, usage = rank_section(provider, bb.brief, t, cands)
        if usage is not None:
            spent += usage.cost(provider.name, Tier.CHEAP)
        rankings[t] = r
        tag = " (unopposed)" if r.get("unopposed") else ""
        print(f"  {t:<18} -> {r['winner']}{tag}")

    brief_text = to_design_brief(comm, primary, why, rankings, registers)
    dest = PROJECTS / bb.project_id / "sources" / "design-brief.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(brief_text)
    print(f"\n  written {dest}")

    # Blueprints from what the winning sources were measured doing — the last
    # hand-written link in the chain.
    from sparrow.agents.blueprinter import Blueprinter, to_markdown

    bp_dir = PROJECTS / bb.project_id / "blueprints"
    bp_dir.mkdir(parents=True, exist_ok=True)
    bper = Blueprinter(provider)
    order = comm.typical_order
    print(f"\n  blueprints from ranked sources:")
    for i, t in enumerate(order):
        r = rankings.get(t)
        if not r:
            continue
        neighbours = [x for x in order if x != t]
        bp, usage = bper.write(bb.brief, t, r, by_type.get(t, []), neighbours)
        spent += usage.cost(provider.name, bper.tier)
        comp = "".join(w.capitalize() for w in t.replace("-", " ").split())
        (bp_dir / f"{i + 1:02d}-{t}.md").write_text(to_markdown(bp, comp))
        print(f"    {t:<18} {len(bp.slots)} slots · {len(bp.structure.split())} words")

    print(f"\n  written {bp_dir}\n  scout cost ${spent:.4f}")
    return 0


CHROME_SKIP_ASSETS = {"nav", "footer"}


def cmd_assets(args) -> int:
    """Produce the imagery the blueprints ask for."""
    from sparrow.agents.curator import Curator, derive_variants
    from sparrow.blackboard.schema import Asset, Prominence, Provenance
    from sparrow.blueprints import load_dir

    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    if bb.design_system is None:
        print("no design_system on the blackboard", file=sys.stderr)
        return 1

    blueprints = load_dir(Path(args.blueprints))
    ws = _workspace(bb.project_id)
    public = ws / "public" / "assets"
    public.mkdir(parents=True, exist_ok=True)

    cur = Curator()
    made: list[Asset] = []
    print(f"curator · {IMAGE_MODEL_NOTE}\n")

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
            if args.limit and len(made) >= args.limit:
                break
            aid = f"{section.id}-{i}"
            png = cur.generate(brief, bb.design_system)
            path = public / f"{aid}.png"
            path.write_bytes(png)
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
            variants = derive_variants(path)
            prom = (Prominence.DOMINANT if len(bp.assets) == 1
                    else Prominence.SUPPORTING if i == 1 else Prominence.THUMBNAIL)
            a = Asset(
                id=aid, section_id=section.id, brief=brief, prominence=prom,
                provenance=Provenance.GENERATED,
                path=f"assets/{path.name}", width=w, height=h,
                variants={k: f"assets/{v}" for k, v in variants.items()},
            )
            made.append(a)
            print(f"  {aid:<22} {w}x{h}  {path.stat().st_size//1024:>4} KB  "
                  f"+{len(variants)} variants  [{prom.value}]")
            print(f"    {brief[:96]}")

    bb.assets = made
    Path(args.blackboard).write_text(bb.model_dump_json(indent=2))
    print(f"\n  {len(made)} asset(s) in {public}")
    print("  provenance: generated — invented by construction, so no text gate applies")
    return 0


IMAGE_MODEL_NOTE = "gpt-image-2 · generated assets are not text-gated; restyles are"


def cmd_inspect(args) -> int:
    """Deterministic pass first, then one vision call per section."""
    from sparrow.agents.inspector import Inspector, deterministic_defects
    from sparrow.blueprints import load_dir
    from sparrow.capture import inspect_page, serve

    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    ws = _workspace(bb.project_id)
    shots_dir = ws.parent / "shots" / "sections"
    blueprints = load_dir(Path(args.blueprints)) if args.blueprints else {}

    with serve(ws / "out", port=args.port) as url:
        reports = inspect_page(url, shots_dir)

    page_level = deterministic_defects(reports)
    print(f"deterministic pass — {len(page_level)} finding(s), 0 model calls")
    for d in page_level:
        print(f"  {d}")

    # Group per-section shots across breakpoints by DOM order.
    by_index: dict[int, list] = {}
    for r in reports.values():
        for s in r.sections:
            by_index.setdefault(s.section_index, []).append(s)

    ordered = sorted(bb.sections, key=lambda s: s.order)
    inspector = Inspector()
    total, found = 0.0, 0
    print(f"\nvision pass — provider {inspector.provider.name} · "
          f"tier {inspector.tier.value}")

    for pos, idx in enumerate(sorted(by_index)):
        shots = by_index[idx]
        section = ordered[pos] if pos < len(ordered) else None
        if section is None:
            continue
        defects, usage = inspector.inspect_section(
            bb, section, shots, page_level, blueprints.get(section.blueprint_id))
        cost = usage.cost(inspector.provider.name, inspector.tier)
        total += cost
        found += len(defects)
        imgs = sum(s.image_tokens for s in shots)
        cached = f" ({usage.cache_hit_rate:.0%} cached)" if usage.cached_tokens else ""
        print(f"\n  {section.id:14} {len(shots)} shot(s), ~{imgs:,} image tokens  "
              f"{usage.total_input:,} in{cached}  ${cost:.4f}")
        for d in defects:
            print(f"      {d}")
        if not defects:
            print("      pass")

    print(f"\n  {found} visual defect(s) · vision cost ${total:.4f}")
    return 0


def cmd_shoot(args) -> int:
    from sparrow.capture import capture, serve

    out = Path(args.out)
    with serve(Path(args.dir)) as url:
        for shot in capture(url, out):
            flag = f"  ⚠ {len(shot.hidden_elements)} still transparent" if shot.hidden_elements else ""
            print(f"{shot.breakpoint:8} {shot.path}{flag}")
    return 0


def main() -> int:
    load_dotenv(ROOT / "backend" / ".env")
    p = argparse.ArgumentParser(prog="sparrow")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="create a project workspace from the scaffold")
    n.add_argument("project")
    n.set_defaults(fn=cmd_new)

    for name, fn, helptext in [
        ("tokens", cmd_tokens, "render design_system into the workspace stylesheet"),
        ("prompt", cmd_prompt, "print the design_system prompt fragment"),
    ]:
        s = sub.add_parser(name, help=helptext)
        s.add_argument("blackboard")
        s.set_defaults(fn=fn)

    a = sub.add_parser("audit", help="deterministic drift audit over built sections")
    a.add_argument("blackboard")
    a.add_argument("--sections", default=None)
    a.set_defaults(fn=cmd_audit)

    b = sub.add_parser("build", help="build every pending section, one call each")
    b.add_argument("blackboard")
    b.add_argument("--blueprints", required=True)
    b.set_defaults(fn=cmd_build)

    sv = sub.add_parser("serve", help="run the HTTP API for the frontend")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--reload", action="store_true")
    sv.set_defaults(fn=cmd_serve)

    rn = sub.add_parser("run", help="drive a project through the pipeline")
    rn.add_argument("project")
    rn.add_argument("--url", action="append", default=[], help="reference site (repeatable)")
    rn.add_argument("--yes", action="store_true", help="auto-answer gates with the first option")
    rn.set_defaults(fn=cmd_run)

    sc = sub.add_parser("scout", help="extract and rank reference sites against the brief")
    sc.add_argument("blackboard")
    sc.add_argument("urls", nargs="+")
    sc.add_argument("--shots", action="store_true", help="also capture per-section screenshots")
    sc.set_defaults(fn=cmd_scout)

    a = sub.add_parser("assets", help="produce the imagery the blueprints ask for")
    a.add_argument("blackboard")
    a.add_argument("--blueprints", required=True)
    a.add_argument("--limit", type=int, default=0, help="stop after N assets")
    a.set_defaults(fn=cmd_assets)

    i = sub.add_parser("inspect", help="deterministic checks, then one vision call per section")
    i.add_argument("blackboard")
    i.add_argument("--port", type=int, default=4402)
    i.add_argument("--blueprints", default=None,
                   help="blueprint dir — without it the inspector cannot judge omissions")
    i.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("shoot", help="scroll-then-capture a static export")
    s.add_argument("dir", help="directory of the static export (out/)")
    s.add_argument("--out", default="shots")
    s.set_defaults(fn=cmd_shoot)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

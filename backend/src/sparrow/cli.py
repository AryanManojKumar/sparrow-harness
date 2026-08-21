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
from sparrow.render.tokens import apply_to_stylesheet, to_prompt

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
    css = _workspace(bb.project_id) / "src/app/globals.css"
    css.write_text(apply_to_stylesheet(css.read_text(), bb.design_system))
    print(f"tokens written to {css}")
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
        out = builder.build(bb, section, bp, stack=stack, available_primitives=primitives)
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

    total += _repair_until_builds(bb, ws, builder.provider.name)
    print(f"\n  total ${total:.4f}")
    return 0


_FAILED_FILE = re.compile(r"\./(src/components/sections/\w+\.tsx)")


def _run_build(ws: Path) -> tuple[bool, str]:
    r = subprocess.run(["pnpm", "build"], cwd=ws, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


def _repair_until_builds(bb, ws: Path, provider_name: str, max_attempts: int = 3) -> float:
    """Build, and if it fails, hand the error back to the repairer.

    Capped at 3 — the same cap as every other loop in the harness. A build that
    still fails after three attempts is an escalation, not a retry.
    """
    from sparrow.agents.builder import Repairer, write_section

    spent = 0.0
    repairer: Repairer | None = None

    for attempt in range(1, max_attempts + 1):
        ok, output = _run_build(ws)
        if ok:
            print(f"\n  build ok{'' if attempt == 1 else f' after {attempt - 1} repair(s)'}")
            return spent

        m = _FAILED_FILE.search(output)
        if not m:
            print(f"\n  build failed, and no section could be blamed:\n{output[-800:]}",
                  file=sys.stderr)
            return spent

        rel = m.group(1)
        section = next((s for s in bb.sections if s.target_path == rel), None)
        if section is None:
            print(f"\n  build failed in {rel}, which is not a known section", file=sys.stderr)
            return spent

        first = output.find("Export ")
        err = output[max(0, first - 200):][:2500] if first > 0 else output[-2500:]
        print(f"\n  build failed in {section.id} — repairing (attempt {attempt}/{max_attempts})")

        repairer = repairer or Repairer()
        out = repairer.repair(bb, section, (ws / rel).read_text(), err)
        write_section(ws, section, out.code)
        cost = out.usage.cost(provider_name, repairer.tier)
        spent += cost
        print(f"     repaired  {out.usage.input_tokens:,} in  "
              f"{out.usage.output_tokens:,} out  ${cost:.4f}")

    print(f"\n  still failing after {max_attempts} attempts — escalate", file=sys.stderr)
    return spent


def cmd_inspect(args) -> int:
    """Deterministic pass first, then one vision call per section."""
    from sparrow.agents.inspector import Inspector, deterministic_defects
    from sparrow.capture import inspect_page, serve

    bb = Blackboard.model_validate_json(Path(args.blackboard).read_text())
    ws = _workspace(bb.project_id)
    shots_dir = ws.parent / "shots" / "sections"

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
        defects, usage = inspector.inspect_section(bb, section, shots, page_level)
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

    i = sub.add_parser("inspect", help="deterministic checks, then one vision call per section")
    i.add_argument("blackboard")
    i.add_argument("--port", type=int, default=4402)
    i.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("shoot", help="scroll-then-capture a static export")
    s.add_argument("dir", help="directory of the static export (out/)")
    s.add_argument("--out", default="shots")
    s.set_defaults(fn=cmd_shoot)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

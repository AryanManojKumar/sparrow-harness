"""sparrow — command line entry point.

Deliberately thin. The loop lives in the modules; this only wires them together
so the whole thing can be exercised without an HTTP layer. FastAPI arrives when
there is a UI to serve, not before.
"""

from __future__ import annotations

import argparse
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

    s = sub.add_parser("shoot", help="scroll-then-capture a static export")
    s.add_argument("dir", help="directory of the static export (out/)")
    s.add_argument("--out", default="shots")
    s.set_defaults(fn=cmd_shoot)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

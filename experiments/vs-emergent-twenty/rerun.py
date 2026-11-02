"""Rebuild twenty-crm after the crop and type checks, from the image step.

What changes against the first build:
- the owner's images carry no `--` crops and the dossier says to show them whole;
- VERIFY measures the page: an image showing under 60% of itself, or a largest
  heading under 85% of the main reference's, is sent back as a fix;
- the main reference is attio.com, as the owner told Emergent. The sources
  stage is not re-run (it is the expensive groundwork); the marker it wrote is
  set to the owner's choice, which is what the agent build reads.

The workshop's copy is replaced by a fresh push, so the agent starts from the
scaffold again, not from the first build.

    cd backend && uv run --extra workshop python ../experiments/vs-emergent-twenty/rerun.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(HERE))

from sparrow import agent_build, api, gateway, steps  # noqa: E402
from sparrow.orchestrator import Stage  # noqa: E402

from run import PID, log  # noqa: E402

MAIN = "attio.com"


def main() -> None:
    run = api._run_for(PID)
    (run.dir / steps.MAIN_REFERENCE).write_text(f"https://{MAIN}/")
    (run.dir / "sources" / "primary.txt").write_text(MAIN)
    for f in ("studio.json", agent_build.MARK, "verify-findings.json"):
        (run.dir / f).unlink(missing_ok=True)
    run.set_pending(None)
    bb = steps._bb(run)
    dropped = steps.reset_assets(run, [a.id for a in bb.assets if a.kind.value != "logo"])
    log(f"main reference {MAIN} · scale {agent_build.reference_scale(run)} · "
        f"reset {len(dropped)} asset(s)")
    run.stage = Stage.ASSETS

    t0, spent0 = time.time(), run.spent
    for ev in run.advance():
        if ev.kind in ("done", "failed", "awaiting", "blocked") or ev.cost \
                or ev.stage in (Stage.ASSETS, Stage.BUILD, Stage.VERIFY):
            log(f"{ev.stage.value} · {ev.kind} · {ev.message[:200]}"
                + (f" · ${ev.cost:.3f}" if ev.cost else ""))
        if ev.kind == "failed":
            raise SystemExit(f"stage failed: {ev.message}")
    out = {"seconds": round(time.time() - t0), "spent_usd": round(run.spent - spent0, 2),
           "agent_usage": gateway.usage_since(PID, t0),
           "preview": f"http://localhost:3000/projects/{PID}/preview/"}
    (HERE / "rerun.json").write_text(json.dumps(out, indent=2))
    log(json.dumps(out))


if __name__ == "__main__":
    main()

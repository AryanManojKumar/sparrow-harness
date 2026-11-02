"""Run VERIFY again on twenty-crm's current site, with the covered-text and
motion checks added after the second build.

    cd backend && uv run --extra workshop python ../experiments/vs-emergent-twenty/reverify.py
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

from sparrow import api, gateway  # noqa: E402
from sparrow.orchestrator import Stage  # noqa: E402

from run import PID, log  # noqa: E402


def main() -> None:
    run = api._run_for(PID)
    run.set_pending(None)
    run.stage = Stage.VERIFY
    t0, spent0 = time.time(), run.spent
    for ev in run.advance():
        if ev.kind in ("done", "failed", "awaiting", "blocked") or ev.cost \
                or ev.stage is Stage.VERIFY:
            log(f"{ev.stage.value} · {ev.kind} · {ev.message[:300]}"
                + (f" · ${ev.cost:.3f}" if ev.cost else ""))
    out = {"seconds": round(time.time() - t0), "spent_usd": round(run.spent - spent0, 2),
           "agent_usage": gateway.usage_since(PID, t0)}
    (HERE / "reverify.json").write_text(json.dumps(out, indent=2))
    log(json.dumps(out))


if __name__ == "__main__":
    main()

"""dsh-builder-04: Sparrow IDE through the agent-designed pipeline, after the speed work.

Same brief, references and logo as sparrow-ide-v3 (built by the old section
builder), so speed and quality compare directly. Images and video generated.
Adapted from dsh-builder-03.

    cd backend && uv run --extra workshop python ../experiments/dsh-builder-04/run.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from sparrow import api, gateway, steps  # noqa: E402  (loads backend/.env)
from sparrow.orchestrator import Stage  # noqa: E402

PID = "sparrow-ide-v4"
BRIEF = dict(
    project_id=PID,
    product_name="Sparrow",
    category="AI developer tool landing page",
    offering=("An agentic IDE that lets solo developers assemble multiple AI agents into a "
              "coordinated team. The agents communicate with one another in a multilevel "
              "system to help build larger products."),
    audience=("Solo developers who want to ship products beyond what they can build alone and "
              "are looking for AI agents that can coordinate as a development team."),
    tone=("Write with ambitious, builder-focused conviction: make the possibility of operating "
          "an AI development team feel concrete and motivating, while explaining multi-agent "
          "coordination plainly rather than relying on vague AI hype."),
    primary_action="Start building with a team of agents",
    secondary_action="See how agents coordinate",
    constraints=[],
    urls=["https://deepseek.com/harness/en/", "https://antigravity.google/", "https://cursor.com/"],
)
LOGO = ROOT / "projects" / "sparrow-ide-v3" / "uploads" / "nav-logo.png"


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def answer(run) -> None:
    gate = run.pending.gate
    if gate is Stage.GATE_BRIEF:
        name = steps.record_product_name(run, BRIEF["product_name"])
        run.resolve({"product_name": name})
        log(f"gate:brief → {name}")
    elif gate is Stage.GATE_DESIGN:
        steps.adopt_direction(run, 0)
        run.resolve({"choice": 0, "note": ""})
        log("gate:design → direction 0")
    elif gate is Stage.GATE_ASSETS:
        decisions = {}
        for a in steps.load_plan(run):
            allowed = steps.decisions_for(a)
            kind = steps._kind(a)
            if kind == "logo" and LOGO.is_file():
                steps.record_upload(run, a["id"], LOGO.name, LOGO.read_bytes())
                decisions[a["id"]] = "upload"
                continue
            want = "generate"
            decisions[a["id"]] = want if want in allowed else (
                "skip" if "skip" in allowed else allowed[-1])
        steps.record_content_answers(run, {})
        steps.record_asset_decisions(run, decisions)
        run.resolve({"assets": decisions})
        log(f"gate:assets → {decisions}")
    else:
        raise AssertionError(f"unexpected gate {gate}")


def main() -> None:
    if not (ROOT / "projects" / PID / "blackboard.json").exists():
        api.create_project(api.CreateProject(**BRIEF))
        log(f"created {PID}")
    run = api._run_for(PID)
    t0 = time.time()
    stages: dict[str, float] = {}
    while True:
        for ev in run.advance():
            stages.setdefault(ev.stage.value, time.time())
            if ev.kind in ("done", "failed", "awaiting", "stopped", "blocked") or ev.cost \
                    or ev.stage in (Stage.BUILD, Stage.VERIFY):
                log(f"{ev.stage.value} · {ev.kind} · {ev.message[:160]}"
                    + (f" · ${ev.cost:.3f}" if ev.cost else ""))
            if ev.kind == "failed":
                raise SystemExit(f"stage failed: {ev.message}")
        if run.pending is None:
            break
        if run.pending.gate is Stage.GATE_PREVIEW:
            log(f"preview gate: {run.pending.question}")
            break
        answer(run)
    agent = gateway.usage_since(PID, t0)
    out = {"seconds": round(time.time() - t0), "pipeline_spent_usd": round(run.spent, 2),
           "agent_usage": agent, "stage_started_at": stages,
           "preview": f"http://localhost:3000/projects/{PID}/preview/"}
    (HERE / "run.json").write_text(json.dumps(out, indent=2))
    log(json.dumps({k: v for k, v in out.items() if k != "stage_started_at"}))


if __name__ == "__main__":
    main()

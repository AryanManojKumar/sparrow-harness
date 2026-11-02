"""dsh-builder-03: the first B2B run of the agent-designed pipeline (B+).

dsh-builder-02 decided the architecture on one game site and said the first
real run should be a different category. This is that run: a new B2B SaaS
brief, the whole pipeline driven to the preview gate — scout, design, content,
material gate, curator, then the agent build and Sparrow's guardrails.

Gates are answered the way a cost-conscious owner with no files would: product
name as given, the first direction, a wordmark instead of a logo, every image
generated, no video, drafted copy kept. Usage and time are written to
`run.json`.

    cd backend && uv run --extra workshop python ../experiments/dsh-builder-03/run.py
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

PID = "b2b-tracewell"
BRIEF = dict(
    project_id=PID,
    product_name="Tracewell",
    category="B2B SaaS landing page",
    offering=("Tracewell is API monitoring for platform teams: it watches every endpoint "
              "a company runs, traces slow and failing requests back to the service and "
              "deploy that caused them, and alerts the owning team before customers notice."),
    audience=("Platform and SRE leads at software companies with dozens of internal and "
              "public APIs, who are tired of finding outages from customer tickets."),
    tone="Calm, exact and technical — confident without hype, written for engineers.",
    primary_action="Start free",
    secondary_action="Book a demo",
    constraints=[
        "do not invent customers, customer logos, testimonials, metrics, pricing, "
        "certifications, integrations or funding",
        "no stock photos of people",
    ],
    urls=["https://linear.app/", "https://vercel.com/", "https://resend.com/"],
)


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
            want = ("wordmark" if kind == "logo" else
                    "skip" if kind in ("video", "portrait") else "generate")
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

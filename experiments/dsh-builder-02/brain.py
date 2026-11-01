"""dsh-builder-02, part 1: run Sparrow's brain on a new FPS project and stop at BUILD.

Everything upstream of the builder runs for real — scout, ranker, design director,
composer, content editor, curator — and every gate is answered the way the earlier
MananShooter runs answered them (logo uploaded, every other asset generated). The
run is halted the moment the BUILD stage starts, before any section is written, so
C (DeepSeek from the build plan) and B (DeepSeek from a prompt) build from the same
point. Sparrow's own builder never runs here.

    uv run --extra workshop python ../experiments/dsh-builder-02/brain.py
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from sparrow import api, steps  # noqa: E402  (loads backend/.env)
from sparrow.orchestrator import Stage  # noqa: E402

PID = "fps-shooter"
BRIEF = dict(
    project_id=PID,
    product_name="MananShooter",
    category="tactical first-person shooter game landing page",
    offering=("MananShooter, a tactical first-person shooter: tight gunplay, round-based "
              "team matches where positioning, utility and precision decide every fight."),
    audience=("Competitive and core FPS players who want to see the gunplay, the maps, the "
              "operators and the feel of a match before they play."),
    tone=("Sharp, high-stakes and confident: competitive intensity with clean precision — "
          "cinematic, never cluttered or cartoonish."),
    primary_action="Play now",
    secondary_action="Watch the trailer",
    constraints=[
        "a tactical first-person shooter called MananShooter",
        "do not invent platforms, release dates, prices, review scores, awards, player "
        "counts, studios or partners",
        "all imagery is AI-generated key art and atmosphere; the logo is the supplied file",
    ],
    urls=["https://www.counter-strike.net/cs2", "https://playvalorant.com/en-us/",
          "https://www.reachthefinals.com/"],
)
LOGO = ROOT / "projects" / "mananshooter" / "uploads" / "nav-logo.png"


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def create() -> None:
    if (ROOT / "projects" / PID / "blackboard.json").exists():
        log(f"{PID} exists — resuming where it stopped")
        return
    api.create_project(api.CreateProject(**BRIEF))
    log(f"created {PID}")


def answer(run) -> None:
    gate = run.pending.gate
    if gate is Stage.GATE_BRIEF:
        name = steps.record_product_name(run, BRIEF["product_name"])
        run.resolve({"product_name": name})
        log(f"gate:brief → product name {name}")
    elif gate is Stage.GATE_DESIGN:
        # The first direction: the design director orders them, and choosing is
        # the human's job only in the product — here it would bias the test.
        steps.adopt_direction(run, 0)
        run.resolve({"choice": 0, "note": ""})
        log("gate:design → direction 0")
    elif gate is Stage.GATE_ASSETS:
        plan = steps.load_plan(run)
        decisions = {}
        for a in plan:
            if steps._kind(a) == "logo" and LOGO.is_file():
                steps.record_upload(run, a["id"], LOGO.name, LOGO.read_bytes())
                decisions[a["id"]] = "upload"
            else:
                allowed = steps.decisions_for(a)
                # A portrait is never generated (Sparrow's rule, and it matches a
                # game "operator portrait" too). With no file to upload: skip it.
                decisions[a["id"]] = ("generate" if "generate" in allowed
                                      else "skip" if "skip" in allowed else allowed[0])
        steps.record_content_answers(run, {})
        steps.record_asset_decisions(run, decisions)
        run.resolve({"assets": decisions})
        log(f"gate:assets → {decisions}")
    else:
        run.resolve({"choice": "approve"})
        log(f"{gate.value} → approve")


def drive() -> None:
    run = api._run_for(PID)
    t0 = time.time()
    while True:
        if run.stage is Stage.BUILD:
            log(f"reached BUILD — brain done in {round(time.time() - t0)}s, "
                f"${run.spent:.2f} spent; Sparrow's builder not run")
            return
        stopped = False
        for ev in run.advance():
            if ev.stage is Stage.BUILD and ev.kind == "started":
                stopped = True
                break  # closing the generator here leaves the stage at BUILD
            if ev.kind in ("done", "failed", "awaiting", "stopped") or ev.cost:
                log(f"{ev.stage.value} · {ev.kind} · {ev.message[:140]}"
                    + (f" · ${ev.cost:.3f}" if ev.cost else ""))
            if ev.kind == "failed":
                raise SystemExit(f"stage failed: {ev.message}")
        if stopped:
            continue
        if run.pending is not None:
            answer(run)


if __name__ == "__main__":
    create()
    drive()

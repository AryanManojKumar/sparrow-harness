"""vs-emergent-twenty: a real product, its own material, against Emergent.

Twenty (the open-source CRM, github.com/twentyhq/twenty) stands in for a real
owner: its logo and its seven product images from the repo are what our
material gate asks for, and the brief says only what its README says. Emergent
gets the same brief, references and files (`PROMPT.md`, `assets/`).

Gates are answered as that owner: product name as given, the first direction,
the logo and every product image uploaded and used exactly as they are
(they are already public), a slot with no matching image generated, no video,
no portrait, no answers to the copy questions (so unconfirmed drafts are
retracted). twenty.com is deliberately not a reference.

    cd backend && uv run --extra workshop python ../experiments/vs-emergent-twenty/run.py
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

PID = "twenty-crm"
ASSETS = HERE / "assets"
BRIEF = dict(
    project_id=PID,
    product_name="Twenty",
    category="B2B SaaS landing page",
    offering=(
        "Twenty is the #1 open-source CRM. It gives technical teams the building blocks "
        "for a custom CRM that meets complex business needs and quickly adapts as the "
        "business evolves: the CRM you build, ship, and version like the rest of your "
        "stack. Objects, fields, views, workflows and AI agents are defined as code with "
        "the Twenty CLI and SDK and published to a workspace; changes go through version "
        "control like any other code. It includes all the tools of a good CRM: custom data "
        "model, Kanban views, custom workflows, sorts and filters, email and calendar sync, "
        "and live dashboards, plus AI agents and chats. Sign up at twenty.com and spin up "
        "a workspace in under a minute with no infrastructure to manage, or self-host it "
        "with Docker Compose."),
    audience=(
        "Technical teams at growing companies whose sales and operations have outgrown an "
        "off-the-shelf CRM, and who want to customise their CRM in code rather than in "
        "settings screens."),
    tone="Confident, precise and developer-friendly. Plain statements, no hype.",
    primary_action="Get started",
    secondary_action="Self-host with Docker",
    constraints=[
        "do not invent customers, customer logos, testimonials, metrics, pricing, "
        "certifications or integrations",
        "no stock photos of people",
    ],
    urls=["https://attio.com/", "https://linear.app/", "https://supabase.com/"],
    main_reference="https://attio.com/",
)

# What the owner says each file shows — the same lines Emergent is given.
CAPTIONS = {
    "1-cover-cli-and-workspace.png": "The CLI next to a Twenty workspace (wide banner)",
    "2-create-your-apps.png": "Create your apps: building front-end components with a "
                              "coding agent and committing them",
    "3-version-control.png": "Stay on top with version control: pull requests and the app's code",
    "4-building-blocks.png": "All the tools you need to build anything: data model, logic "
                             "and layout building blocks",
    "5-customize-layouts.png": "Customize your layouts: record pages and widgets",
    "6-ai-agents-and-chats.png": "AI agents and chats: choosing models, an AI agent in a "
                                 "workflow, Ask AI",
    "7-all-the-crm-tools.png": "Plus all the tools of a good CRM: data model, Kanban, "
                               "workflows, filters, email sync, dashboards",
}

# The owner's files, each with the words that say where it belongs.
IMAGES = [
    ("1-cover-cli-and-workspace.png", "hero overview workspace product cli"),
    ("2-create-your-apps.png", "app build component developer code ai coding"),
    ("3-version-control.png", "version git commit pull request ship deploy review"),
    ("4-building-blocks.png", "data model object field logic building block layout views"),
    ("5-customize-layouts.png", "layout widget record page customize dashboard"),
    ("6-ai-agents-and-chats.png", "agent ai chat assistant model"),
    ("7-all-the-crm-tools.png", "crm kanban workflow pipeline filter email calendar feature"),
]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def pick_images(plan: list[dict]) -> dict[str, str]:
    """Each image slot gets the owner's file that fits it best, each file once."""
    slots = [a for a in plan if steps._kind(a) == "image"]
    left = list(IMAGES)
    chosen: dict[str, str] = {}

    def score(a: dict, words: str) -> int:
        text = f"{a['section_id']} {a['brief']}".lower()
        return sum(w in text for w in words.split())

    for a in sorted(slots, key=lambda a: a["section_id"] != "hero"):
        if not left:
            break
        best = max(left, key=lambda f: score(a, f[1]))
        chosen[a["id"]] = best[0]
        left.remove(best)
    return chosen


def add_the_rest(run) -> None:
    """The owner's images no slot asked for, added with their captions."""
    plan = steps.load_plan(run)
    if any(a.get("extra") for a in plan):
        return
    # Which files went into the planned slots, written at the gate.
    taken = set(json.loads((HERE / "slotted.json").read_text()))
    for f, _ in IMAGES:
        if f in taken:
            continue
        e = steps.add_owner_image(run, f, (ASSETS / f).read_bytes(), CAPTIONS[f])
        steps.record_asset_decisions(run, {e["id"]: "as_is"})
        log(f"  {e['id']}: as_is ← {f} · {CAPTIONS[f]}")


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
        plan = steps.load_plan(run)
        files = pick_images(plan)
        decisions = {}
        for a in plan:
            kind = steps._kind(a)
            if kind == "logo":
                logo = ASSETS / "twenty-logo.svg"
                steps.record_upload(run, a["id"], logo.name, logo.read_bytes())
                decisions[a["id"]] = "upload"
            elif a["id"] in files:
                f = ASSETS / files[a["id"]]
                steps.record_upload(run, a["id"], f.name, f.read_bytes())
                decisions[a["id"]] = "as_is"
            elif kind in ("video", "portrait"):
                decisions[a["id"]] = "skip"
            else:
                decisions[a["id"]] = "generate"
            log(f"  {a['id']} ({a['section_id']}): {decisions[a['id']]}"
                + (f" ← {files[a['id']]}" if a["id"] in files else "")
                + f" · {a['brief'][:90]}")
        steps.record_content_answers(run, {})
        steps.record_asset_decisions(run, decisions)
        (HERE / "slotted.json").write_text(json.dumps(sorted(files.values())))
        add_the_rest(run)
        run.resolve({"assets": decisions})
        log(f"gate:assets → {decisions}")
    else:
        raise AssertionError(f"unexpected gate {gate}")


def main() -> None:
    if not (ROOT / "projects" / PID / "blackboard.json").exists():
        api.create_project(api.CreateProject(**BRIEF))
        log(f"created {PID}")
    run = api._run_for(PID)
    if steps.load_plan(run) and run.stage is Stage.ASSETS:
        add_the_rest(run)       # resuming a run whose gate predates extra images
    t0 = time.time()
    stages: dict[str, float] = {}
    while True:
        for ev in run.advance():
            stages.setdefault(ev.stage.value, time.time())
            if ev.kind in ("done", "failed", "awaiting", "stopped", "blocked") or ev.cost \
                    or ev.stage in (Stage.ASSETS, Stage.BUILD, Stage.VERIFY):
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

"""HTTP surface for the harness.

Thin on purpose. Every endpoint either reads the blackboard or advances the run;
no logic lives here that is not about HTTP.

The shape follows from the three gates. A run is not a request/response — it takes
minutes and stops twice for a human — so the frontend starts it, streams progress,
and answers gates. Progress arrives over SSE because that is the smallest thing
that works in a browser without a socket.

    POST   /projects                      create from a brief + reference urls
    GET    /projects                      list
    GET    /projects/{id}                 blackboard + current stage
    POST   /projects/{id}/advance         run until the next gate (SSE stream)
    GET    /projects/{id}/gate            what is being asked, and the options
    POST   /projects/{id}/gate            answer it
    GET    /projects/{id}/directions      the design proposals at gate 2
    GET    /projects/{id}/preview/*       the built site, served statically
    GET    /projects/{id}/shots/{name}    captures
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from pydantic import BaseModel

from sparrow import telemetry
from sparrow.blackboard.schema import Blackboard, Brief, Constraint
from sparrow.orchestrator import Run, Stage
from sparrow import steps

ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = ROOT / "scaffold"
PROJECTS = ROOT / "projects"

# Swagger's assets are vendored rather than pulled from jsdelivr. A CDN turns
# "the API docs" into something that depends on the network, an adblocker, and a
# corporate proxy all cooperating — and when it fails it fails as a blank page,
# which reads as "swagger is broken" rather than "a script did not load".
STATIC = Path(__file__).parent / "static"

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title="sparrow",
    version="0.1.0",
    description=(
        "Builds a business website from a brief and real reference sites.\n\n"
        "A run is not request/response — it takes ~12 minutes and stops twice for a "
        "human. Start it, stream progress, answer the gates.\n\n"
        "**brief → [GATE 1] → sources → design → [GATE 2] → assets → build → verify "
        "→ [GATE 3] → done**\n\n"
        "A full run costs roughly $1.10. Every event carries its own cost and the "
        "running total."
    ),
    openapi_tags=[
        {"name": "elicitation", "description":
         "The front of the funnel. Nothing is generated until a brief exists."},
        {"name": "projects", "description": "Create and read."},
        {"name": "run", "description":
         "Drive the pipeline and answer gates. `/advance` streams SSE — use curl -N "
         "or EventSource, not the Try-it-out panel, which buffers."},
        {"name": "artifacts", "description": "The built site and its captures."},
    ],
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Live runs, by project id. A halted run keeps its place here so the gate answer
# lands on the same object; losing it costs a re-read of the blackboard, not work.
_RUNS: dict[str, Run] = {}

# A run continues after the client disconnects, deliberately: the work is already
# paid for and a closed tab should not throw away eight minutes of extraction. But
# that makes double-advance reachable — reconnect, press go again, and two
# generators drive the same stages concurrently, writing the same files and
# double-charging. One advance per project at a time.
_ADVANCING: set[str] = set()


class SuggestRequest(BaseModel):
    q: str
    limit: int = 5

    model_config = {"json_schema_extra": {"examples": [
        {"q": "a website for my compliance", "limit": 5}]}}


class InterviewRequest(BaseModel):
    prompt: str

    model_config = {"json_schema_extra": {"examples": [{"prompt":
        "a site for my SOC 2 compliance startup, we sell to fintech engineers "
        "who have been through a painful audit. dont use blue, our competitor is blue"}]}}


class CreateProject(BaseModel):
    project_id: str
    category: str
    offering: str
    audience: str
    tone: str
    primary_action: str
    secondary_action: str | None = None
    constraints: list[str] = []
    urls: list[str] = []

    model_config = {"json_schema_extra": {"examples": [{
        "project_id": "acme",
        "category": "Developer tool landing page",
        "offering": "An agent harness for codebases. Runs a fleet of coding agents "
                    "under a shared plan, every change reviewable as a diff.",
        "audience": "Staff engineers at teams of 20-200 who found a coding agent "
                    "unreviewable at scale.",
        "tone": "Precise and technical. No hype about velocity. THE STRONGEST FIELD "
                "HERE — it moves the design more than anything else.",
        "primary_action": "Start free",
        "secondary_action": "Read the docs",
        "constraints": ["no purple - every dev tool is purple"],
        "urls": ["https://kiro.dev", "https://cursor.com"]}]}}


class GateAnswer(BaseModel):
    """At gate 2 `choice` is a direction index; elsewhere it is approve/revise."""

    choice: str | int
    note: str | None = None

    model_config = {"json_schema_extra": {"examples": [
        {"choice": 0, "note": "the ledger direction"},
        {"choice": "approve"}]}}


def _run_for(pid: str) -> Run:
    if pid in _RUNS:
        return _RUNS[pid]
    if not (PROJECTS / pid / "blackboard.json").exists():
        raise HTTPException(404, f"no project {pid!r}")
    urls = json.loads((PROJECTS / pid / "urls.json").read_text()) \
        if (PROJECTS / pid / "urls.json").exists() else []
    run = Run(pid, ROOT, {
        Stage.BRIEF: steps.step_brief,
        Stage.SOURCES: lambda r: steps.step_sources(r, urls),
        Stage.DESIGN: steps.step_design,
        Stage.ASSETS: steps.step_assets,
        Stage.BUILD: steps.step_build,
        Stage.VERIFY: steps.step_verify,
    })
    _RUNS[pid] = run
    return run


@app.middleware("http")
async def log_requests(request, call_next):
    """Every request, with its duration and the trace it belongs to.

    The project id is pulled out of the path so an HTTP line lands in the same
    per-project log as the model calls it caused — otherwise you have two
    records of one run and no way to line them up.
    """
    import time as _t

    parts = request.url.path.strip("/").split("/")
    project = parts[1] if len(parts) > 1 and parts[0] == "projects" else None
    t0 = _t.perf_counter()
    with telemetry.trace(project or "_api"):
        try:
            response = await call_next(request)
        except Exception as e:
            telemetry.log_error(f"{request.method} {request.url.path}", e)
            raise
        telemetry.log_http(
            request.method, request.url.path, response.status_code,
            int((_t.perf_counter() - t0) * 1000),
            query=str(request.url.query) or None,
        )
        return response


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/docs", include_in_schema=False)
def swagger() -> Any:
    return get_swagger_ui_html(
        openapi_url="/openapi.json", title="sparrow — API",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.svg",
    )


@app.get("/redoc", include_in_schema=False)
def redoc() -> Any:
    return get_redoc_html(
        openapi_url="/openapi.json", title="sparrow — API",
        redoc_js_url="/static/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.svg",
    )


@app.post("/suggest", tags=["elicitation"], summary="Autocomplete a half-typed prompt")
def suggest(body: SuggestRequest) -> dict[str, Any]:
    """Autocomplete for the prompt box.

    Completions aim at what is still UNKNOWN about the business, not at a website
    shape. A page shape chosen before the business is understood is a template, and
    the point of §2 is that this system does not hand people templates. `gap` says
    which of offering / audience / specifics / purpose it aimed at, so the interface
    can show what the brief still needs.

    An accelerator, never a step: it returns empty rather than an error on anything
    going wrong, because a failed completion must not interrupt typing.
    """
    from sparrow.agents.interviewer import Interviewer

    return Interviewer().suggest(body.q, body.limit)


@app.post("/interview", tags=["elicitation"], summary="Turn one sentence into a brief (does not create the project)")
def interview(body: InterviewRequest) -> dict[str, Any]:
    """One sentence in, a structured brief out — plus what had to be assumed.

    Deliberately does NOT create the project. The user sees the brief, corrects the
    assumptions, and only then commits: CLAUDE.md §2, nothing is generated until the
    brief exists and is right.
    """
    from sparrow.agents.interviewer import BriefDraft

    brief, constraints, assumed, confidence = BriefDraft().interview(body.prompt)
    return {
        "brief": brief.model_dump(mode="json"),
        "constraints": [c.text for c in constraints],
        "assumed": assumed,
        "confidence": confidence,
    }


@app.post("/projects", tags=["projects"], summary="Create a project from a brief and reference urls")
def create_project(body: CreateProject) -> dict[str, Any]:
    d = PROJECTS / body.project_id
    if (d / "blackboard.json").exists():
        raise HTTPException(409, "project already exists")
    d.mkdir(parents=True, exist_ok=True)
    bb = Blackboard(
        project_id=body.project_id,
        brief=Brief(category=body.category, offering=body.offering,
                    audience=body.audience, tone=body.tone,
                    primary_action=body.primary_action,
                    secondary_action=body.secondary_action),
        constraints=[Constraint(id=f"c{i+1}", text=t)
                     for i, t in enumerate(body.constraints)],
    )
    (d / "blackboard.json").write_text(bb.model_dump_json(indent=2))
    (d / "urls.json").write_text(json.dumps(body.urls))
    steps.make_workspace(_run_for(body.project_id), SCAFFOLD)
    return {"project_id": body.project_id, "stage": Stage.BRIEF.value}


@app.get("/projects", tags=["projects"], summary="List projects")
def list_projects() -> list[dict[str, Any]]:
    """One unreadable project must not take down the list.

    Blackboards written before a schema change do not validate against the current
    models — `Color.name` and the three font roles were both added mid-flight. A
    listing endpoint that 500s because one old record exists is worse than one that
    reports the record as unreadable.
    """
    out = []
    for p in sorted(PROJECTS.glob("*/blackboard.json")):
        try:
            bb = Blackboard.model_validate_json(p.read_text())
        except Exception as e:
            out.append({"project_id": p.parent.name, "readable": False,
                        "reason": f"{type(e).__name__}: schema drift — "
                                  f"written by an older version"})
            continue
        out.append({"project_id": bb.project_id, "readable": True,
                    "version": bb.version, "sections": len(bb.sections),
                    "has_design_system": bb.design_system is not None,
                    "assets": len(bb.assets)})
    return out


@app.get("/projects/{pid}", tags=["projects"], summary="Blackboard, stage, spend and recent log")
def get_project(pid: str) -> dict[str, Any]:
    run = _run_for(pid)
    bb = Blackboard.model_validate_json(run.blackboard_path.read_text())
    return {
        "project_id": pid,
        "stage": run.stage.value,
        "advancing": pid in _ADVANCING,
        "spent": round(run.spent, 4),
        "awaiting_gate": run.pending.gate.value if run.pending else None,
        "blackboard": bb.model_dump(mode="json"),
        "log": [{"stage": e.stage.value, "kind": e.kind, "message": e.message,
                 "cost": e.cost} for e in run.log[-60:]],
    }


@app.post("/projects/{pid}/advance", tags=["run"], summary="Run until the next gate (SSE stream)")
def advance(pid: str) -> StreamingResponse:
    """Run until the next gate. Server-sent events, one per stage transition.

    The run keeps going if the client disconnects — closing a tab should not throw
    away work already paid for. Reconnect with `GET /projects/{id}` for the current
    stage and the log so far.

    A second advance while one is in flight is refused rather than queued, because
    two generators over the same stages write the same files and bill twice.
    """
    run = _run_for(pid)
    if pid in _ADVANCING:
        raise HTTPException(
            409,
            "this project is already advancing — reconnect with GET /projects/"
            f"{pid} to follow it, or wait for it to reach a gate",
        )

    def stream():
        _ADVANCING.add(pid)
        try:
            for ev in run.advance():
                payload = {"stage": ev.stage.value, "kind": ev.kind,
                           "message": ev.message, "cost": ev.cost, "data": ev.data,
                           "spent": round(run.spent, 4)}
                yield f"data: {json.dumps(payload)}\n\n"
            yield "event: end\ndata: {}\n\n"
        finally:
            _ADVANCING.discard(pid)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/projects/{pid}/gate", tags=["run"], summary="What the run is waiting for, and the options")
def get_gate(pid: str) -> dict[str, Any]:
    run = _run_for(pid)
    if run.pending is None:
        return {"awaiting": False}
    r = run.pending
    return {"awaiting": True, "gate": r.gate.value, "question": r.question,
            "options": r.options, "artifacts": r.artifacts}


@app.post("/projects/{pid}/gate", tags=["run"], summary="Answer the open gate")
def answer_gate(pid: str, body: GateAnswer) -> dict[str, Any]:
    run = _run_for(pid)
    if run.pending is None:
        raise HTTPException(409, "no gate is open")
    if run.pending.gate is Stage.GATE_DESIGN:
        try:
            steps.adopt_direction(run, int(body.choice))
        except (ValueError, TypeError, IndexError):
            raise HTTPException(400, "choice must be a direction index")
    run.resolve({"choice": body.choice, "note": body.note})
    return {"stage": run.stage.value}


@app.get("/projects/{pid}/directions", tags=["run"], summary="The three design directions proposed at gate 2")
def directions(pid: str) -> list[dict[str, Any]]:
    p = PROJECTS / pid / "directions.json"
    if not p.exists():
        raise HTTPException(404, "no directions proposed yet")
    return json.loads(p.read_text())


@app.get("/projects/{pid}/preview/{path:path}", tags=["artifacts"], summary="The built site, static — drop in an iframe")
def preview(pid: str, path: str = "") -> FileResponse:
    base = (PROJECTS / pid / "workspace" / "out").resolve()
    target = (base / (path or "index.html")).resolve()
    if not str(target).startswith(str(base)):      # no traversal out of the export
        raise HTTPException(403, "outside the preview root")
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        raise HTTPException(404, path)
    return FileResponse(target)


@app.get("/projects/{pid}/shots/{name}", tags=["artifacts"], summary="A capture")
def shot(pid: str, name: str) -> FileResponse:
    base = (PROJECTS / pid / "shots").resolve()
    target = (base / name).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        raise HTTPException(404, name)
    return FileResponse(target)


@app.get("/projects/{pid}/logs", tags=["artifacts"],
         summary="Replay a project's log — every request, stage and model call")
def logs(pid: str, kind: str | None = None, limit: int = 500) -> dict[str, Any]:
    kinds = {k.strip() for k in kind.split(",")} if kind else None
    return {"project_id": pid, "events": telemetry.read_run(pid, kinds, limit)}


@app.get("/projects/{pid}/logs/summary", tags=["artifacts"],
         summary="What a run cost, broken down by agent")
def logs_summary(pid: str) -> dict[str, Any]:
    return telemetry.summarise_run(pid)


@app.get("/health", tags=["projects"], summary="Liveness")
def health() -> dict[str, str]:
    return {"status": "ok"}

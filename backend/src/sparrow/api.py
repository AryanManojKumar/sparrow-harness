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

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from sparrow.blackboard.schema import Blackboard, Brief, Constraint
from sparrow.orchestrator import Run, Stage
from sparrow import steps

ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = ROOT / "scaffold"
PROJECTS = ROOT / "projects"

app = FastAPI(title="sparrow", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Live runs, by project id. A halted run keeps its place here so the gate answer
# lands on the same object; losing it costs a re-read of the blackboard, not work.
_RUNS: dict[str, Run] = {}


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


class GateAnswer(BaseModel):
    choice: str | int
    note: str | None = None


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


@app.post("/projects")
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


@app.get("/projects")
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


@app.get("/projects/{pid}")
def get_project(pid: str) -> dict[str, Any]:
    run = _run_for(pid)
    bb = Blackboard.model_validate_json(run.blackboard_path.read_text())
    return {
        "project_id": pid,
        "stage": run.stage.value,
        "spent": round(run.spent, 4),
        "awaiting_gate": run.pending.gate.value if run.pending else None,
        "blackboard": bb.model_dump(mode="json"),
        "log": [{"stage": e.stage.value, "kind": e.kind, "message": e.message,
                 "cost": e.cost} for e in run.log[-60:]],
    }


@app.post("/projects/{pid}/advance")
def advance(pid: str) -> StreamingResponse:
    """Run until the next gate. Server-sent events, one per stage transition."""
    run = _run_for(pid)

    def stream():
        for ev in run.advance():
            payload = {"stage": ev.stage.value, "kind": ev.kind,
                       "message": ev.message, "cost": ev.cost, "data": ev.data,
                       "spent": round(run.spent, 4)}
            yield f"data: {json.dumps(payload)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/projects/{pid}/gate")
def get_gate(pid: str) -> dict[str, Any]:
    run = _run_for(pid)
    if run.pending is None:
        return {"awaiting": False}
    r = run.pending
    return {"awaiting": True, "gate": r.gate.value, "question": r.question,
            "options": r.options, "artifacts": r.artifacts}


@app.post("/projects/{pid}/gate")
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


@app.get("/projects/{pid}/directions")
def directions(pid: str) -> list[dict[str, Any]]:
    p = PROJECTS / pid / "directions.json"
    if not p.exists():
        raise HTTPException(404, "no directions proposed yet")
    return json.loads(p.read_text())


@app.get("/projects/{pid}/preview/{path:path}")
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


@app.get("/projects/{pid}/shots/{name}")
def shot(pid: str, name: str) -> FileResponse:
    base = (PROJECTS / pid / "shots").resolve()
    target = (base / name).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        raise HTTPException(404, name)
    return FileResponse(target)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

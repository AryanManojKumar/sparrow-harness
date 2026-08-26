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
    GET    /projects/{id}/assets          the per-image plan at the asset gate
    POST   /projects/{id}/assets/{aid}    upload the user's own image (multipart)
    GET    /projects/{id}/preview/*       the built site, served statically
    GET    /projects/{id}/shots/{name}    captures
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from pydantic import BaseModel

from sparrow import telemetry
from sparrow.blackboard.schema import Blackboard, BuildStatus, Brief, Constraint
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
        "**brief → [GATE 1] → sources → design → [GATE 2] → [ASSET GATE] → assets "
        "→ build → verify → [GATE 3] → done**\n\n"
        "The asset gate is per-image, not per-run: upload your own, generate one, "
        "or skip it. It is the only point at which the user's real material can "
        "enter the run.\n\n"
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

# Big enough for a 4K dashboard screenshot, small enough that a mistyped upload
# does not fill the disk. The image model resizes to 1536x1024 anyway.
MAX_UPLOAD = 25_000_000

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
    # Carried from /interview. Without it every builder invents its own name and
    # the page ships with a different product in the nav than in the footer —
    # observed as LedgerRoute vs Railform on one page. The Brief field existed;
    # this request model did not have it, so it was extracted and then dropped
    # on the floor between the two calls.
    product_name: str = ""
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
        "product_name": "Acme Harness",
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
    """At gate 2 `choice` is a direction index; elsewhere it is approve/revise.

    At the ASSET gate neither is used: `assets` carries one decision per image.
    A single `choice` cannot express the answer, and that is the whole point of
    the gate — a founder has a real dashboard screenshot for the hero and
    nothing at all for the integrations strip. One global choice would force
    them to fabricate the second or lose the first.
    """

    choice: str | int | None = None
    note: str | None = None
    # At GATE 1, when the interviewer could not extract a name from the prompt.
    # It is the only field that gate takes, and it is required there: measured
    # across eight real projects, `product_name` was "" on every one and the
    # sites shipped anonymous while their generated screenshots invented brands
    # of their own.
    product_name: str | None = None
    assets: dict[str, str] | None = None    # asset_id -> upload | generate | skip
                                            # nav-logo -> upload | wordmark
    content: dict[str, str] | None = None   # ask_id -> the user's real answer
                                            # (omit or empty to keep the draft)

    model_config = {"json_schema_extra": {"examples": [
        {"product_name": "Acme Harness"},
        {"choice": 0, "note": "the ledger direction"},
        {"assets": {"nav-logo": "upload", "hero-1": "upload",
                    "feature-grid-1": "generate", "feature-grid-2": "skip"}},
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
        # CONTENT was missing from this map while the CLI had it, so every run
        # driven through the API skipped the copy stage entirely: no drafted
        # slots, no provenance, and `content_asks` empty at the material gate,
        # which made half of that gate silently unreachable. A stage absent from
        # this dict is not an error — `_advance` treats it as a gate with
        # nothing pending and steps over it.
        Stage.CONTENT: steps.step_content,
        Stage.GATE_ASSETS: steps.step_asset_gate,
        Stage.ASSETS: steps.step_assets,
        Stage.BUILD: steps.step_build,
        Stage.VERIFY: steps.step_verify,
    })
    # Resume where the project actually got to. Without this a server restart
    # sends every project back to `brief`, and the next /advance re-extracts
    # every reference site — a whole run's cost, spent silently, for nothing.
    try:
        bb = Blackboard.model_validate_json(
            (PROJECTS / pid / "blackboard.json").read_text())
        run.stage = Stage(bb.stage)
        if run.stage is Stage.BRIEF:
            run.stage = _infer_stage(PROJECTS / pid, bb)
    except (ValueError, KeyError):
        pass          # an unknown stage string: start from the top, as before
    _RUNS[pid] = run
    return run


def _infer_stage(d: Path, bb: Blackboard) -> Stage:
    """Where a project got to, for one written before the stage was recorded.

    `Blackboard.stage` defaults to "brief", and every project built before it
    existed carries that default — nine finished sites all reporting they had
    not started. Clicking one made the next /advance re-extract every reference
    site and re-run the whole pipeline: a full run's cost, for a project that
    was already built.

    Read from artifacts on disk rather than trusting the default, and only ever
    when the recorded stage IS the default — a project genuinely sitting at
    brief has none of these.
    """
    if (d / "workspace/out/index.html").is_file():
        # It has a built, exported site. Whatever else is true, the pipeline is
        # past the point where re-running it is free.
        return Stage.GATE_PREVIEW
    if bb.sections and bb.design_system is not None:
        return Stage.BUILD
    if bb.design_system is not None:
        return Stage.GATE_DESIGN
    if (d / "blueprints").is_dir() and any((d / "blueprints").iterdir()):
        return Stage.DESIGN
    if bb.brief is not None:
        return Stage.SOURCES
    return Stage.BRIEF


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
        brief=Brief(product_name=body.product_name.strip(),
                    category=body.category, offering=body.offering,
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
    for f in PROJECTS.glob("*/blackboard.json"):
        d = f.parent
        # The DIRECTORY name, never bb.project_id. Every URL in this API is
        # keyed by the directory, and a project copied from another carries the
        # original's id inside its blackboard — `_assetgate-live` says
        # "crossborder-e2e" and the listing showed two rows with one id, either
        # of which navigated to the wrong project.
        row: dict[str, Any] = {
            "project_id": d.name,
            "updated_at": f.stat().st_mtime,
            # What the UI needs to decide whether a card is clickable at all.
            "has_preview": (d / "workspace/out/index.html").is_file(),
        }
        try:
            bb = Blackboard.model_validate_json(f.read_text())
        except Exception as e:
            # Blackboards written before a schema change do not validate against
            # the current models. A listing that 500s because one old record
            # exists is worse than one that reports the record as unreadable.
            row |= {"readable": False,
                    "reason": f"{type(e).__name__}: schema drift — "
                              f"written by an older version"}
            out.append(row)
            continue
        brief = bb.brief
        row |= {
            "readable": True,
            "product_name": (brief.product_name if brief else "") or "",
            "category": brief.category if brief else "",
            # The stage the run would actually RESUME at, not the raw field.
            # A project written before the stage was recorded carries the
            # default "brief" while having a finished site on disk, and a UI
            # that believes it offers to start a run that is already done.
            "stage": (bb.stage if bb.stage != Stage.BRIEF.value
                      else _infer_stage(d, bb).value),
            "version": bb.version,
            "sections": len(bb.sections),
            "built": sum(1 for x in bb.sections if x.status is BuildStatus.BUILT),
            "has_design_system": bb.design_system is not None,
            "assets": len(bb.assets),
        }
        out.append(row)
    # Most recently touched first: a list of a dozen projects in directory order
    # buries the one the user was just working on.
    out.sort(key=lambda r: r["updated_at"], reverse=True)
    return out


class BriefPatch(BaseModel):
    """A correction to the brief on a project that is already past gate 1."""

    product_name: str

    model_config = {"json_schema_extra": {"examples": [
        {"product_name": "voiceowl.ai"}]}}


@app.patch("/projects/{pid}/brief", tags=["projects"],
           summary="Correct the brief after gate 1 has closed")
def patch_brief(pid: str, body: BriefPatch) -> dict[str, Any]:
    """Settle a name on a project that has already been built.

    Gate 1 is where the name is normally settled, and `record_product_name` is
    reachable only while that gate is open. Every project built before the name
    existed is therefore stuck with `product_name: ""` and no way to correct it
    except a full re-run — which is the wrong price for one string.

    §4 already has the shape for this: a brief is a document that gets revised,
    and a revision is recorded with what it superseded rather than appended
    beside the old value. `record_product_name` writes through the store, so the
    correction lands in the decision log like any other transition.

    Fixing the name is not enough on its own. Imagery generated before the
    correction still shows whatever the curator guessed, so follow this with
    /rebuild naming those assets — the response says which ones carry a brand.
    """
    run = _run_for(pid)
    if pid in _ADVANCING:
        raise HTTPException(409, "this project is advancing — wait for a gate")
    try:
        name = steps.record_product_name(run, body.product_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"project_id": pid, "product_name": name,
            "next": "imagery generated before this still shows the old name — "
                    "POST /projects/{pid}/rebuild with the assets that carry a brand"}


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
    if run.pending.gate is Stage.GATE_BRIEF:
        try:
            name = steps.record_product_name(run, body.product_name or "")
        except ValueError as e:
            raise HTTPException(400, str(e))
        run.resolve({"product_name": name})
        return {"stage": run.stage.value, "product_name": name}
    if run.pending.gate is Stage.GATE_ASSETS:
        try:
            # Content first: an asset error must not silently discard the real
            # facts the user just typed about their own business.
            replaced = steps.record_content_answers(run, body.content or {})
            plan = steps.record_asset_decisions(run, body.assets or {})
        except ValueError as e:
            raise HTTPException(400, str(e))
        run.resolve({"assets": {a["id"]: a["decision"] for a in plan}})
        return {"stage": run.stage.value,
                "decisions": {a["id"]: a["decision"] for a in plan},
                "content_answered": replaced}
    if run.pending.gate is Stage.GATE_DESIGN:
        # "None of these" sends the run back to DESIGN with the note as guidance,
        # so a rejection produces new directions rather than the same three.
        if str(body.choice) in {"other", "-1"}:
            if not (body.note or "").strip():
                raise HTTPException(
                    400, "say what to change — 'darker', 'warmer', 'less green'")
            (PROJECTS / pid / "redirect.txt").write_text(body.note.strip())
            run.pending = None
            run.stage = Stage.DESIGN
            return {"stage": run.stage.value, "regenerating": True}
        try:
            steps.adopt_direction(run, int(body.choice))
        except (ValueError, TypeError, IndexError):
            raise HTTPException(400, "choice must be a direction index, or 'other'")
    run.resolve({"choice": body.choice, "note": body.note})
    return {"stage": run.stage.value}


class Rebuild(BaseModel):
    """Re-make named parts of a finished project, without re-running the run."""

    sections: list[str] = []
    assets: list[str] = []
    # Where the next /advance picks up. Only the three stages that consume what
    # is ALREADY on the blackboard are allowed: `sources` re-fetches every
    # reference site and `design` re-proposes directions, which is a whole run's
    # cost and a gate the user already answered.
    stage: str = "build"

    model_config = {"json_schema_extra": {"examples": [
        {"sections": ["nav", "footer"], "stage": "build"},
        {"assets": ["hero-1"], "sections": ["hero"], "stage": "assets"}]}}


REBUILDABLE = {Stage.ASSETS, Stage.BUILD, Stage.VERIFY}


@app.post("/projects/{pid}/rebuild", tags=["run"],
          summary="Re-make named sections or assets, then advance from a later stage")
def rebuild(pid: str, body: Rebuild) -> dict[str, Any]:
    """The user-facing half of resume.

    `step_build` keeps a section it has already built and `step_assets` keeps an
    asset it has already produced — both deliberately, because re-running either
    stage on a finished project pays again for what is already on disk. Neither
    had any way to say "but re-make this one", so a correction to a single
    section meant either a full re-run or hand-editing the workspace, and
    hand-editing the workspace puts the blackboard and the site out of sync with
    nothing to detect it.

    This is also the smallest correct path for identity landing on a project
    that is already built: settle the name at gate 1, upload the logo at the
    material gate, then reset the two chrome sections and rebuild from `build`.
    Two builder calls rather than a pipeline.
    """
    run = _run_for(pid)
    if pid in _ADVANCING:
        raise HTTPException(409, "this project is advancing — wait for a gate")
    if run.pending is not None:
        raise HTTPException(409, f"answer the open gate first ({run.pending.gate.value})")
    try:
        stage = Stage(body.stage)
    except ValueError:
        raise HTTPException(400, f"unknown stage {body.stage!r}")
    if stage not in REBUILDABLE:
        raise HTTPException(
            400, f"{stage.value} re-derives from the sources and costs a whole run. "
                 f"Rebuild from one of: {', '.join(sorted(s.value for s in REBUILDABLE))}")
    try:
        assets = steps.reset_assets(run, body.assets) if body.assets else []
        sections = steps.reset_sections(run, body.sections) if body.sections else []
    except ValueError as e:
        raise HTTPException(400, str(e))
    run.stage = stage
    return {"stage": stage.value, "sections_reset": sections,
            "assets_reset": assets,
            "next": f"POST /projects/{pid}/advance"}


@app.get("/projects/{pid}/directions", tags=["run"], summary="The three design directions proposed at gate 2")
def directions(pid: str) -> list[dict[str, Any]]:
    p = PROJECTS / pid / "directions.json"
    if not p.exists():
        raise HTTPException(404, "no directions proposed yet")
    return json.loads(p.read_text())


@app.get("/projects/{pid}/assets", tags=["run"],
         summary="Every image this run needs, and what has been decided for each")
def asset_plan(pid: str) -> list[dict[str, Any]]:
    """The per-image plan the asset gate is asking about.

    Available before the gate is answered and after, so an interface can show
    what was chosen without keeping its own copy.
    """
    run = _run_for(pid)
    # Merged, not loaded: a project finished before a slot existed would
    # otherwise never show it. The voice-ai site was built before the logo slot
    # and its saved plan has no nav-logo in it.
    plan = steps.merged_plan(run) if (run.dir / "blueprints").is_dir() else []
    if not plan:
        raise HTTPException(404, "no asset plan yet — the run has not reached "
                                 "the asset gate")
    return plan


@app.post("/projects/{pid}/assets/{asset_id}", tags=["run"],
          summary="Upload the user's own image for one asset")
async def upload_asset(pid: str, asset_id: str,
                       file: UploadFile = File(...)) -> dict[str, Any]:
    """The user's real material, entering the run.

    Post the file FIRST, then answer the gate with `"upload"` for this asset —
    answering `upload` with no file is refused rather than quietly falling back
    to a generated image, because a silent fallback is exactly how every site in
    this category ends up filled with pictures nobody chose.

    The file is stored untouched. `step_assets` restyles a COPY of it to the
    chosen design direction and checks the restyle for text fidelity; if the
    model invented words, the restyle is discarded and this original ships
    instead. CLAUDE.md §7 — it is still a picture of their real product, so text
    it gains is a claim they never made.
    """
    run = _run_for(pid)
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty upload")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, f"image is larger than {MAX_UPLOAD // 1_000_000}MB")
    try:
        entry = steps.record_upload(run, asset_id, file.filename or "upload.png", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"asset_id": asset_id, "stored": entry["upload"], "bytes": len(data),
            "next": "answer the asset gate with this asset set to 'upload'"}


# HEAD as well as GET. A frontend checking "is there a preview here?" before
# rendering an iframe sends HEAD, and Starlette answers a GET-only route with
# 405 — which reads as "broken" rather than "not built yet". FastAPI derives the
# HEAD response from the GET handler, so the body is never sent.
@app.api_route("/projects/{pid}/preview/{path:path}", methods=["GET", "HEAD"],
               tags=["artifacts"],
               summary="The built site, static — drop in an iframe")
def preview(pid: str, path: str = "") -> Any:
    """Serve the static export under a per-project prefix.

    The export is built for a site root, so its HTML asks for `/_next/static/…`
    and `/assets/…` absolutely. Served at `/projects/{id}/preview/` those all 404
    and the page renders as unstyled text with no images — which looks like the
    build failed rather than like the paths are wrong.

    So root-absolute references in HTML are rewritten to the prefix on the way
    out. Protocol-relative and absolute URLs are left alone. Rewriting on serve
    rather than setting Next's assetPrefix at build time keeps the export
    portable: the same `out/` can be dropped on any host without a rebuild.
    """
    base = (PROJECTS / pid / "workspace" / "out").resolve()
    target = (base / (path or "index.html")).resolve()
    if not str(target).startswith(str(base)):      # no traversal out of the export
        raise HTTPException(403, "outside the preview root")
    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        raise HTTPException(404, path)

    if target.suffix.lower() not in {".html", ".htm"}:
        return FileResponse(target)

    # No rewriting: the export is built with basePath set to this path, so Next
    # already emits the prefix everywhere — including inside the RSC payload,
    # which an HTML rewrite cannot reach.
    return FileResponse(target)


@app.get("/projects/{pid}/specimens/{name}", tags=["artifacts"],
         summary="A rendered design direction, or the source palettes")
def specimen(pid: str, name: str) -> FileResponse:
    base = (PROJECTS / pid / "specimens").resolve()
    target = (base / name).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        raise HTTPException(404, name)
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

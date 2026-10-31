"""The workshop's HTTP surface. Only the office calls it.

    GET    /health                              liveness (no auth)
    GET    /projects/{pid}                      does the workshop hold it, is it busy
    PUT    /projects/{pid}/workspace            import a workspace (tar.gz body)
    GET    /projects/{pid}/workspace            export it back (tar.gz)
    PUT    /projects/{pid}/dossier              AGENTS.md: what the agent knows about the site
    POST   /projects/{pid}/build                next build, jailed
    POST   /projects/{pid}/turns                one studio request (SSE stream)
    GET    /projects/{pid}/pages                the built site's pages
    GET    /projects/{pid}/checkpoints          history, newest first
    POST   /projects/{pid}/undo                 restore the previous checkpoint
    POST   /projects/{pid}/restore/{cid}        restore a named checkpoint
    GET    /projects/{pid}/preview/{path}       the built export

Every route but /health needs `Authorization: Bearer $WORKSHOP_TOKEN`. In
production the host firewall also admits only the office; the token is what
still holds if that rule is ever wrong.

Run it with:  uv run --extra workshop uvicorn --factory sparrow.workshop.app:create_app --port 8100
"""

from __future__ import annotations

import hmac
import json
from typing import Any, Iterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

from sparrow.workshop import store
from sparrow.workshop.config import WorkshopConfig


class TurnBody(BaseModel):
    message: str
    llm_token: str


def create_app(cfg: WorkshopConfig | None = None, studio: Any = None) -> FastAPI:
    cfg = cfg or WorkshopConfig.load()
    cfg.root.mkdir(parents=True, exist_ok=True)
    if studio is None:
        from sparrow.workshop.studio import Studio
        studio = Studio(cfg)
    from sparrow.workshop import studio as studio_mod

    app = FastAPI(title="sparrow workshop", docs_url=None, redoc_url=None)

    def auth(request: Request) -> None:
        got = request.headers.get("authorization", "")
        if not hmac.compare_digest(got.encode(), f"Bearer {cfg.token}".encode()):
            raise HTTPException(401, "unauthorized")

    def proj(pid: str) -> store.Project:
        try:
            return store.project(cfg.root, pid)
        except store.StoreError as e:
            raise HTTPException(400, str(e))

    def held(pid: str) -> store.Project:
        p = proj(pid)
        if not p.exists():
            raise HTTPException(404, "workshop does not hold this project")
        return p

    guarded = [Depends(auth)]

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/projects/{pid}", dependencies=guarded)
    def info(pid: str) -> dict:
        p = proj(pid)
        return {"exists": p.exists(), "busy": studio.busy(pid),
                "has_preview": (p.export / "index.html").is_file()}

    @app.put("/projects/{pid}/workspace", dependencies=guarded)
    async def put_workspace(pid: str, request: Request) -> dict:
        p = proj(pid)
        if studio.busy(pid):
            raise HTTPException(409, "a studio turn is running")
        body = await request.body()
        try:
            store.import_workspace(p, body)
        except store.StoreError as e:
            raise HTTPException(400, str(e))
        return {"ok": True, "checkpoints": store.checkpoints(p, limit=1)}

    @app.get("/projects/{pid}/workspace", dependencies=guarded)
    def get_workspace(pid: str) -> Response:
        return Response(store.pack(held(pid).workspace), media_type="application/gzip")

    @app.put("/projects/{pid}/dossier", dependencies=guarded)
    async def put_dossier(pid: str, request: Request) -> dict:
        p = held(pid)
        text = (await request.body()).decode("utf-8", "replace")
        if len(text) > 200_000:
            raise HTTPException(400, "dossier too large")
        store.write_dossier(p, text)
        return {"ok": True, "bytes": len(text)}

    @app.post("/projects/{pid}/build", dependencies=guarded)
    def build(pid: str) -> dict:
        p = held(pid)
        if studio.busy(pid):
            raise HTTPException(409, "a studio turn is running")
        return studio_mod.build(cfg, p)

    @app.post("/projects/{pid}/turns", dependencies=guarded)
    def turn(pid: str, body: TurnBody) -> StreamingResponse:
        p = held(pid)
        if not body.message.strip():
            raise HTTPException(400, "empty message")
        try:
            events = studio.turn(p, body.message, body.llm_token)
        except studio_mod.Busy:
            raise HTTPException(409, "a studio turn is already running")

        def sse() -> Iterator[str]:
            for e in events:
                yield f"data: {json.dumps(e)}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    @app.get("/projects/{pid}/pages", dependencies=guarded)
    def pages(pid: str) -> list[str]:
        return store.routes(held(pid).export)

    @app.get("/projects/{pid}/checkpoints", dependencies=guarded)
    def checkpoints(pid: str) -> list[dict]:
        return store.checkpoints(held(pid))

    def _restore(pid: str, fn) -> dict:
        p = held(pid)
        if studio.busy(pid):
            raise HTTPException(409, "a studio turn is running")
        try:
            cid = fn(p)
        except store.StoreError as e:
            raise HTTPException(400, str(e))
        return {"checkpoint": cid, "checkpoints": store.checkpoints(p, limit=5)}

    @app.post("/projects/{pid}/undo", dependencies=guarded)
    def undo(pid: str) -> dict:
        return _restore(pid, store.undo)

    @app.post("/projects/{pid}/restore/{cid}", dependencies=guarded)
    def restore(pid: str, cid: str) -> dict:
        return _restore(pid, lambda p: store.restore(p, cid, f"Restored {cid}"))

    @app.api_route("/projects/{pid}/preview/{path:path}", methods=["GET", "HEAD"],
                   dependencies=guarded)
    def preview(pid: str, path: str = "") -> FileResponse:
        root = held(pid).export.resolve()
        target = (root / path).resolve()
        if not target.is_relative_to(root):
            raise HTTPException(403, "outside the preview root")
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            raise HTTPException(404, "not built")
        return FileResponse(target)

    return app

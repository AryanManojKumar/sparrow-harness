"""The LLM gateway: the only way an agent in the workshop reaches a model.

The workshop holds no provider key. When the office starts a studio turn it
mints a token bound to one project and hands it to the workshop; the agent
sends it as an ordinary bearer key, and this gateway swaps it for the real
credential on the way out. A leaked token is worth one project's studio
session for a few hours, against one route, one model — not the office's key.

It runs as its OWN process on its own port, beside the office on the office's
machine:

    uv run uvicorn sparrow.gateway:app --port 8001

because the workshop must be able to reach it and must not be able to reach
the office API. Mounted inside the office it shared a port with
`GET /projects`, and an agent in the jail could read every project's
blackboard with one curl (measured). As a separate listener, the workshop
host's firewall admits this port and nothing else.

Tokens are signed rather than stored, so the office that mints them and the
gateway that checks them share a secret (GATEWAY_SECRET) instead of memory.
There is no revocation; expiry is the bound.

The workshop asks for the model "studio". Which real model that is gets decided
here from `providers.MODELS` — the same table every other agent uses — so
changing the office's provider changes the studio with it, and the workshop
never learns a model name worth caring about.

The gateway speaks OpenAI chat-completions and normalizes the one quirk the
gpt-5 line has (see `OpenAIProvider.complete`): it takes max_completion_tokens
and rejects temperature. A client that does not know "studio" is a gpt-5 model
cannot be expected to know that.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from sparrow.providers import AZURE_APIM_DEFAULT_BASE, MODELS, Tier

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

STUDIO_MODEL = "studio"
TOKEN_TTL = 12 * 3600
# A token with less than this left is replaced rather than reused, so a turn
# never starts on a token that expires halfway through it.
REUSE_MARGIN = 3600
_PID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _secret() -> bytes:
    s = os.environ.get("GATEWAY_SECRET", "")
    if len(s) < 32:
        raise HTTPException(503, "GATEWAY_SECRET is not set (32+ characters)")
    return s.encode()


def _sign(body: str) -> str:
    mac = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


# What a project's agent may generate. One letter per kind so the token stays
# short; the office decides the set when it issues the token (today every kind,
# from STUDIO_ASSET_KINDS; later per user), the gateway enforces it.
ASSET_CAPS = {"image": "i", "video": "v"}


def default_caps() -> str:
    kinds = os.environ.get("STUDIO_ASSET_KINDS", "image,video")
    return "".join(ASSET_CAPS[k.strip()] for k in kinds.split(",") if k.strip() in ASSET_CAPS) or "-"


class Tokens:
    """Signed, project-bound, expiring bearer tokens: `stu.<pid>.<exp>.<caps>.<sig>`.

    `caps` names what the agent holding it may generate (see ASSET_CAPS); it
    is inside the signature, so neither the agent nor the workshop can widen
    it. `issue` remembers the last token per project so a warm agent runtime
    keeps the token it started with; an office restart forgets that, and the
    next turn simply starts the runtime again with a new one.
    """

    def __init__(self) -> None:
        self._last: dict[str, tuple[str, int, str]] = {}
        self._lock = threading.Lock()

    def issue(self, pid: str, caps: str | None = None) -> str:
        if not _PID.match(pid):
            raise ValueError(f"invalid project id {pid!r}")
        caps = caps if caps is not None else default_caps()
        now = int(time.time())
        with self._lock:
            tok, exp, had = self._last.get(pid, ("", 0, ""))
            if exp - now > REUSE_MARGIN and had == caps:
                return tok
            exp = now + TOKEN_TTL
            body = f"{pid}.{exp}.{caps}"
            tok = f"stu.{body}.{_sign(body)}"
            self._last[pid] = (tok, exp, caps)
            return tok

    @staticmethod
    def claims(token: str) -> tuple[str, str] | None:
        """(project, caps) of a valid, unexpired token, or None."""
        parts = token.split(".")
        if len(parts) != 5 or parts[0] != "stu" or not _PID.match(parts[1]):
            return None
        pid, exp, caps, sig = parts[1], parts[2], parts[3], parts[4]
        if not exp.isdigit() or int(exp) <= time.time() or not re.fullmatch(r"[a-z-]{1,8}", caps):
            return None
        if not hmac.compare_digest(sig, _sign(f"{pid}.{exp}.{caps}")):
            return None
        return pid, caps

    @classmethod
    def check(cls, token: str) -> str | None:
        """The project a valid, unexpired token belongs to, or None."""
        c = cls.claims(token)
        return c[0] if c else None


TOKENS = Tokens()


@dataclass(frozen=True)
class Upstream:
    base: str
    headers: dict[str, str]
    model: str


def upstream() -> Upstream:
    """Where studio requests go, derived from the office's provider setting."""
    name = (os.environ.get("SPARROW_PROVIDER") or "openai").lower()
    if name not in MODELS:
        raise HTTPException(503, f"provider {name!r} is unknown")
    model = MODELS[name][Tier.TOP]
    if name == "azure":
        key = os.environ.get("AZURE_APIM_KEY")
        base = os.environ.get("AZURE_APIM_BASE_URL", AZURE_APIM_DEFAULT_BASE)
        headers = {"api-key": key or ""}
    elif name == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        headers = {"authorization": f"Bearer {key}"}
    else:
        # Anthropic does not speak chat-completions natively; the studio agent
        # does. Not worth an adapter until someone runs the office on it.
        raise HTTPException(503, f"the studio gateway does not support provider {name!r}")
    if not key:
        raise HTTPException(503, f"provider {name!r} has no key configured")
    return Upstream(base.rstrip("/"), headers, model)


def normalize(body: dict, model: str) -> dict:
    body = {**body, "model": model}
    if model.startswith("gpt-5"):
        if "max_tokens" in body:
            body.setdefault("max_completion_tokens", body.pop("max_tokens"))
        body.pop("temperature", None)
    return body


router = APIRouter(prefix="/llm/v1", tags=["gateway"], include_in_schema=False)
_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(600, connect=20))
    return _client


@router.post("/chat/completions")
async def chat_completions(request: Request) -> Response:
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    pid = TOKENS.check(token) if token else None
    if pid is None:
        raise HTTPException(401, "invalid or expired studio token")
    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        raise HTTPException(400, "body is not JSON")
    if body.get("model") != STUDIO_MODEL:
        raise HTTPException(400, f"only the {STUDIO_MODEL!r} model is served here")
    up = upstream()
    payload = normalize(body, up.model)
    req = _http().build_request(
        "POST", f"{up.base}/chat/completions", json=payload,
        headers={**up.headers, "content-type": "application/json"})
    r = await _http().send(req, stream=True)
    if r.status_code >= 400:
        err = await r.aread()
        await r.aclose()
        return Response(err, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))

    async def relay():
        try:
            async for chunk in r.aiter_raw():
                yield chunk
        finally:
            await r.aclose()

    return StreamingResponse(relay(), status_code=r.status_code,
                             media_type=r.headers.get("content-type"))


app = FastAPI(title="sparrow gateway", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# ── assets: the agent's generate_asset tool, served over MCP ────────────────
# The studio agent calls this the way it calls any tool; the owner never sees
# an asset screen. It lives here, beside the model route, for the same reason:
# the provider key (ElevenLabs) is the office's, and the agent reaches it only
# through a project-bound token whose signed caps say which kinds it may make.
# Minimal Streamable HTTP: one JSON-RPC request per POST, answered as JSON.

MCP_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
_KIND_SHAPES = {"image": ("wide", "square", "tall"), "video": ("wide", "tall")}

MCP_INSTRUCTIONS = (
    "generate_asset makes new images and short video clips for this website and saves "
    "them into public/assets/. Use it when a change needs imagery that does not exist "
    "yet. Never use it to replace the owner's own photos or product screenshots, and "
    "never for anything that must be read — interface text, data, logos come out as "
    "gibberish. Generated imagery is illustrative: never present it as the owner's real "
    "product, team or customers."
)


def _tool(caps: str) -> dict | None:
    kinds = [k for k, c in ASSET_CAPS.items() if c in caps]
    if not kinds:
        return None
    return {
        "name": "generate_asset",
        "description": (
            "Generate an image" + (" or a short video clip" if "video" in kinds else "")
            + " for the website and save it in public/assets/. Write the prompt like an "
            "art director — subject, composition, light, palette — matched to the imagery "
            "treatment in AGENTS.md. Images take under a minute; video several minutes, so "
            "generate only what the page will use. Returns the src to put in the code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": kinds},
                "prompt": {"type": "string", "description": "What it must show, in detail."},
                "shape": {"type": "string", "enum": ["wide", "square", "tall"],
                          "description": "wide 3:2 (video 16:9) · square 1:1 (images only) · "
                                         "tall 2:3 (video 9:16)"},
                "filename": {"type": "string",
                             "description": "Short lowercase name without extension, e.g. 'pricing-hero'."},
            },
            "required": ["kind", "prompt", "shape", "filename"],
            "additionalProperties": False,
        },
    }


def _ext(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return "png"


def generate_asset(pid: str, caps: str, args: dict) -> tuple[str, bool]:
    """Run one generate_asset call. Returns (text for the agent, is_error)."""
    from sparrow import eleven
    from sparrow.workshop.client import Workshop, WorkshopError

    kind = str(args.get("kind", ""))
    if kind not in ASSET_CAPS:
        return f"kind must be one of {', '.join(ASSET_CAPS)}", True
    if ASSET_CAPS[kind] not in caps:
        return (f"This project is not allowed to generate {kind}. Use existing assets, "
                "or tell the owner it needs their permission."), True
    prompt = str(args.get("prompt", "")).strip()
    if len(prompt) < 12:
        return "prompt is too short — describe what the asset must show", True
    shape = str(args.get("shape", "wide"))
    if shape not in _KIND_SHAPES[kind]:
        return f"shape for {kind} must be one of {', '.join(_KIND_SHAPES[kind])}", True
    stem = re.sub(r"[^a-z0-9-]+", "-", str(args.get("filename", "")).lower()).strip("-")[:50]
    stem = stem or f"{kind}-{int(time.time())}"
    try:
        data = (eleven.generate(prompt[:2000], shape=shape) if kind == "image"
                else eleven.motion(prompt[:2000], shape=shape))
    except Exception as e:  # provider refusal, unapproved model, timeout
        return f"The {kind} could not be generated: {str(e)[:400]}", True
    try:
        saved = Workshop().put_asset(pid, f"{stem}.{_ext(data)}", data)
    except WorkshopError as e:
        return f"The {kind} was generated but could not be saved: {e.detail}", True
    return (f"Saved {saved['path']} ({len(data) // 1024} KB). Use src=\"{saved['src']}\" — "
            f"the base path is required. It is generated: illustrative, never the owner's "
            f"real product, people or customers."), False


def _rpc_result(rid, result) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _rpc_error(rid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


async def _handle(msg: dict, pid: str, caps: str) -> dict | None:
    from starlette.concurrency import run_in_threadpool

    rid, method, params = msg.get("id"), msg.get("method", ""), msg.get("params") or {}
    if rid is None:  # a notification: nothing to answer
        return None
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _rpc_result(rid, {
            "protocolVersion": asked if asked in MCP_PROTOCOLS else MCP_PROTOCOLS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "sparrow-studio", "version": "1"},
            "instructions": MCP_INSTRUCTIONS,
        })
    if method == "ping":
        return _rpc_result(rid, {})
    if method == "tools/list":
        tool = _tool(caps)
        return _rpc_result(rid, {"tools": [tool] if tool else []})
    if method == "tools/call":
        if params.get("name") != "generate_asset" or _tool(caps) is None:
            return _rpc_error(rid, -32602, f"unknown tool {params.get('name')!r}")
        text, is_error = await run_in_threadpool(
            generate_asset, pid, caps, params.get("arguments") or {})
        return _rpc_result(rid, {"content": [{"type": "text", "text": text}], "isError": is_error})
    return _rpc_error(rid, -32601, f"method not found: {method}")


@app.post("/mcp")
async def mcp(request: Request) -> Response:
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    claims = Tokens.claims(token) if token else None
    if claims is None:
        raise HTTPException(401, "invalid or expired studio token")
    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        return Response(json.dumps(_rpc_error(None, -32700, "parse error")),
                        media_type="application/json", status_code=400)
    msgs = body if isinstance(body, list) else [body]
    out = [r for m in msgs if isinstance(m, dict) and (r := await _handle(m, *claims)) is not None]
    if not out:
        return Response(status_code=202)
    payload = out if isinstance(body, list) else out[0]
    return Response(json.dumps(payload), media_type="application/json")


@app.get("/mcp")
def mcp_stream() -> Response:
    # No server-initiated messages: the spec's answer is 405 on the GET stream.
    return Response(status_code=405)


@app.delete("/mcp")
def mcp_end() -> Response:
    return Response(status_code=200)

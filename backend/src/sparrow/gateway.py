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


class Tokens:
    """Signed, project-bound, expiring bearer tokens: `stu.<pid>.<exp>.<sig>`.

    `issue` remembers the last token per project so a warm agent runtime keeps
    the token it started with; an office restart forgets that, and the next
    turn simply starts the runtime again with a new one.
    """

    def __init__(self) -> None:
        self._last: dict[str, tuple[str, int]] = {}
        self._lock = threading.Lock()

    def issue(self, pid: str) -> str:
        if not _PID.match(pid):
            raise ValueError(f"invalid project id {pid!r}")
        now = int(time.time())
        with self._lock:
            tok, exp = self._last.get(pid, ("", 0))
            if exp - now > REUSE_MARGIN:
                return tok
            exp = now + TOKEN_TTL
            body = f"{pid}.{exp}"
            tok = f"stu.{body}.{_sign(body)}"
            self._last[pid] = (tok, exp)
            return tok

    @staticmethod
    def check(token: str) -> str | None:
        """The project a valid, unexpired token belongs to, or None."""
        parts = token.split(".")
        if len(parts) != 4 or parts[0] != "stu" or not _PID.match(parts[1]):
            return None
        pid, exp, sig = parts[1], parts[2], parts[3]
        if not exp.isdigit() or int(exp) <= time.time():
            return None
        if not hmac.compare_digest(sig, _sign(f"{pid}.{exp}")):
            return None
        return pid


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

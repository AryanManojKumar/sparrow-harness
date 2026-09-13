"""KIE.ai image generation and editing.

Why this exists alongside `providers.py`: KIE is not a chat provider and does
not fit the Tier abstraction. It is an asynchronous job queue — createTask hands
back a taskId, and recordInfo is polled until `state` leaves "waiting". Nothing
streams and nothing blocks server-side, so every call here costs a round trip
plus however long the model takes.

Three things cost an afternoon to discover, so they are written down:

1. `image_urls` is an ARRAY, always. Passing `image_url` (singular) fails with
   "image_urls is required", which reads like the field is missing rather than
   misnamed.
2. `image_urls` will NOT take a `data:` URI — the API answers "File type not
   supported". Bytes have to be uploaded first and referenced by the URL the
   uploader returns, which is what `upload()` is for.
3. The model allowlist is per account and is not published. An unsupported name
   returns 422 "model name you specified is not supported"; a supported one with
   an empty input returns 500 naming the first missing field. That difference is
   the only catalogue there is — `google/nano-banana-2-lite`, which the gallery
   page in this repo documents, is not on this account.

Model ids verified live against the account, 2026-09-02.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request

# Cloudflare sits in front of both hosts and rejects urllib's default
# User-Agent with "error code: 1010" — a 403 that looks like an auth failure and
# is not one. Every request here sets a UA for that reason, uploads included.
UA = "sparrow/1.0"

JOBS = "https://api.kie.ai/api/v1/jobs"
UPLOAD = "https://kieai.redpandaai.co/api/file-base64-upload"

# Text-to-image and image-to-image are different models, not different modes of
# one model. Both are overridable so a benchmark can move them without a code
# change, the same way provider tiers are.
GEN_MODEL = os.environ.get("KIE_IMAGE_MODEL", "qwen3/pro-text-to-image")
EDIT_MODEL = os.environ.get("KIE_EDIT_MODEL", "google/nano-banana-edit")

# curator asks for a shape, not a resolution. gpt-image-2's sizes were 1536x1024,
# 1024x1024 and 1024x1536 — 3:2, 1:1 and 2:3. KIE takes aspect ratios directly
# and happens to offer exactly those three, so the framing of every existing
# blueprint survives the provider switch unchanged.
SHAPES = {"wide": "3:2", "square": "1:1", "tall": "2:3"}

POLL_INTERVAL = 3.0
TIMEOUT = 300.0


class KieError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("KIE_API_KEY")
    if not k:
        raise RuntimeError("KIE_API_KEY is not set")
    return k


def _post(url: str, body: dict, *, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {_key()}",
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise KieError(f"{url} -> HTTP {e.code}: {e.read()[:300].decode(errors='replace')}") from e


def _fetch(url: str, *, timeout: float = 120.0) -> bytes:
    """Download a result image.

    The result CDN 403s on urllib's default User-Agent. curl gets through and
    Python does not, which makes this look like an expiring-URL or auth problem
    rather than what it is — so the header is not optional.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get(url: str, *, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {_key()}", "User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def upload(png: bytes, *, name: str = "image.png") -> str:
    """Put bytes somewhere KIE can fetch them, and return that URL.

    The edit models take URLs only, so this is not an optimisation — it is the
    only way local bytes reach them.
    """
    res = _post(
        UPLOAD,
        {
            "base64Data": "data:image/png;base64," + base64.b64encode(png).decode(),
            "uploadPath": "images/sparrow",
            "fileName": name,
        },
        timeout=120.0,
    )
    url = (res.get("data") or {}).get("downloadUrl")
    if not url:
        raise KieError(f"upload returned no downloadUrl: {json.dumps(res)[:300]}")
    return url


def _run(model: str, payload: dict) -> bytes:
    """createTask, poll to a terminal state, download the first result."""
    res = _post(f"{JOBS}/createTask", {"model": model, "input": payload})
    if res.get("code") != 200:
        raise KieError(f"createTask {model}: {res.get('code')} {res.get('msg')}")
    task = res["data"]["taskId"]

    deadline = time.monotonic() + TIMEOUT
    while True:
        d = _get(f"{JOBS}/recordInfo?taskId={task}").get("data") or {}
        state = d.get("state")
        if state == "success":
            urls = json.loads(d["resultJson"])["resultUrls"]
            if not urls:
                raise KieError(f"task {task} succeeded with no resultUrls")
            return _fetch(urls[0])
        if state == "fail":
            raise KieError(f"task {task} failed: {d.get('failCode')} {d.get('failMsg')}")
        if time.monotonic() > deadline:
            raise KieError(f"task {task} still {state!r} after {TIMEOUT:.0f}s")
        time.sleep(POLL_INTERVAL)


def generate(prompt: str, *, shape: str = "wide", resolution: str = "2K") -> bytes:
    """Text to image.

    `prompt_extend` is off. It is on by default and rewrites the prompt to
    "improve results for simple descriptions" — but curator's prompts are not
    simple descriptions. They carry the design system, the product name, and an
    explicit instruction not to invent branding. A rewrite is free to drop any
    of that, and the failure is silent: a plausible image that ignores half its
    constraints.
    """
    return _run(
        GEN_MODEL,
        {
            "prompt": prompt,
            "image_size": SHAPES.get(shape, "3:2"),
            "resolution": resolution,
            "output_format": "png",
            "prompt_extend": False,
        },
    )


def edit(prompt: str, images: list[bytes], *, shape: str = "wide") -> bytes:
    """Image to image, with one or more reference images.

    Callers pass raw PNG bytes; the upload round trip is hidden here so the call
    sites read the same as the OpenAI ones they replaced.
    """
    if not images:
        raise ValueError("edit() needs at least one image")
    urls = [upload(b, name=f"ref{i}.png") for i, b in enumerate(images)]
    return _run(
        EDIT_MODEL,
        {
            "prompt": prompt,
            "image_urls": urls,
            "image_size": SHAPES.get(shape, "3:2"),
            "output_format": "png",
        },
    )

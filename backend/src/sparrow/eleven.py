"""ElevenLabs generative media — images now, video when a section asks for it.

Sibling to `kie.py`, same shape: create a generation, poll until it leaves
`pending`, download the result. Different provider, different reason for
existing — KIE's `qwen3/pro-text-to-image` renders convincing dashboard LAYOUTS
with gibberish LABELS, which is fatal for a harness whose whole thesis is real
content. `gpt-image-2` renders `const token = req.cookies.get('session')?.value`
and a test row reading `getSession returns null for missing cookie · 85ms · PASS`.
For a product screenshot that difference is the product.

Access is per WORKSPACE, not per key, and the two failures look nothing alike:

- `model_not_approved` — the workspace has not enabled that model. A new key
  will not fix it; an administrator has to approve it. Measured on this account:
  gpt-image-2 approved, every other image model and veo-3.1-fast not.
- a 422 with `extra_forbidden` — the BODY is wrong for that model. Validation
  runs BEFORE the approval check, so a 422 says nothing about whether the model
  is available. Reading one as evidence of the other wastes an hour.

`aspect_ratio` is 3:2 / 1:1 / 2:3, which is exactly curator's wide / square /
tall, so the shape vocabulary survives the provider change untouched.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://api.elevenlabs.io/v1/flows"

IMAGE_MODEL = os.environ.get("ELEVEN_IMAGE_MODEL", "gpt-image-2")
VIDEO_MODEL = os.environ.get("ELEVEN_VIDEO_MODEL", "veo-3.1-generate-001")

# curator asks for a shape. These are the three it has always asked for.
SHAPES = {"wide": "3:2", "square": "1:1", "tall": "2:3"}

POLL_INTERVAL = 5.0
TIMEOUT = 600.0


class ElevenError(RuntimeError):
    pass


def _key() -> str:
    # The env var was written lowercase by hand more than once. Accept both
    # rather than fail on a name, but prefer the conventional one.
    k = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("elevenlabs")
    if not k:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    return k


def _req(url: str, body: dict | None = None, *, timeout: float = 180.0) -> dict:
    r = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"xi-api-key": _key(), "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ElevenError(
            f"{url} -> HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"
        ) from e


def _fetch(url: str, *, timeout: float = 180.0, attempts: int = 4) -> bytes:
    """Download a finished generation. Retries, because by the time this runs
    the generation is complete and billed — an SSL handshake timeout on the
    download (measured, once, on a 19MB clip) threw away a paid render that
    was sitting on the server waiting to be fetched again."""
    req = urllib.request.Request(url, headers={"User-Agent": "sparrow/1.0"})
    last: Exception | None = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(3 * (i + 1))
    raise ElevenError(f"download failed after {attempts} attempts: {last}")


def _run(kind: str, payload: dict) -> bytes:
    """Create, poll to a terminal state, download. `kind` is "image" or "video".

    Every exit from this function is logged — success, provider failure, and
    timeout alike. It is the only choke point both media paths pass through, so
    instrumenting it here is what makes a four-minute video call visible in the
    run log instead of looking like a stall.
    """
    from sparrow import telemetry

    started = time.monotonic()
    model = payload.get("model_id", "?")
    prompt = str(payload.get("prompt", ""))
    # Every knob that changes what comes back, so a surprising result can be
    # explained from the log without re-deriving what was sent.
    params = {k: v for k, v in payload.items()
              if k in ("aspect_ratio", "resolution", "quality", "seed",
                       "generate_audio", "negative_prompt")}
    if payload.get("images"):
        params["refs"] = len(payload["images"])

    def _fail(msg: str) -> ElevenError:
        telemetry.log_media(
            kind=kind, provider="elevenlabs", model=model, prompt=prompt,
            duration_ms=int((time.monotonic() - started) * 1000),
            error=msg[:200], **params)
        return ElevenError(msg)

    try:
        res = _req(f"{BASE}/{kind}", payload)
    except Exception as e:
        raise _fail(f"create failed: {str(e)[:180]}") from e
    gid = res.get("id")
    if not gid:
        raise _fail(f"{kind}: no generation id in {json.dumps(res)[:200]}")
    telemetry.log_stage(kind, "progress", f"{kind} {gid} accepted by {model}")

    deadline = time.monotonic() + TIMEOUT
    seen = None
    while True:
        st = _req(f"{BASE}/{kind}/{gid}")
        status = st.get("status")
        # Transitions only. Polling every 5s for 155s would otherwise put 31
        # identical "pending" lines in the log for one video.
        if status != seen:
            telemetry.log_stage(kind, "progress",
                                f"{kind} {gid} {seen or 'new'} → {status}")
            seen = status
        if status in ("completed", "complete", "succeeded", "success"):
            url = st.get("content_url")
            if not url:
                raise _fail(f"{kind} {gid} finished with no content_url")
            blob = _fetch(url)
            telemetry.log_media(
                kind=kind, provider="elevenlabs", model=model, prompt=prompt,
                duration_ms=int((time.monotonic() - started) * 1000),
                bytes_out=len(blob), generation_id=gid, **params)
            return blob
        if status in ("failed", "error"):
            raise _fail(f"{kind} {gid} failed: {json.dumps(st)[:200]}")
        if time.monotonic() > deadline:
            raise _fail(f"{kind} {gid} still {status!r} after {TIMEOUT:.0f}s")
        time.sleep(POLL_INTERVAL)


def generate(prompt: str, *, shape: str = "wide", quality: str = "medium",
             resolution: str = "1K", images: list[bytes] | None = None) -> bytes:
    """Text to image, or image-to-image when references are supplied.

    medium/1K by default, measured rather than assumed: high/2K takes 117s,
    medium/1K 65s, low/1K 37s — and medium renders a diff whose semantics hold
    up (TTL 7 days to 14, randomBytes(32) to randomBytes(48), a userAgentHash
    added) with a test panel reading "5 passed (1.2s)". Paying 117s buys nothing
    a reader can see.

    One call covers both because `gpt-image-2` takes reference images on the
    same endpoint — unlike KIE, where text-to-image and image-to-image are
    different models with different required fields, and the references have to
    be uploaded and passed as URLs first.
    """
    body: dict = {
        "model_id": IMAGE_MODEL,
        "prompt": prompt,
        "aspect_ratio": SHAPES.get(shape, "3:2"),
        "quality": quality,
        "resolution": resolution,
    }
    if images:
        import base64

        # {type, content_base64, mime_type} — all three required. The first
        # version of this guessed {data, mime_type} and would have failed at the
        # one call site that matters, the logo-branding path, on a live run.
        body["images"] = [
            {"type": "inline_base64", "content_base64": base64.b64encode(b).decode(),
             "mime_type": "image/png"}
            for b in images[:10]
        ]
    return _run("image", body)


# The video endpoint's shapes. Only two, unlike `SHAPES` — there is no square
# video on this model, and asking for one is a 422.
VIDEO_SHAPES = {"wide": "16:9", "tall": "9:16"}


def motion(prompt: str, *, shape: str = "wide", resolution: str = "1080p",
           negative_prompt: str = "", seed: int | None = None,
           audio: bool = False) -> bytes:
    """Text to video. Returns mp4 bytes.

    Ambient footage, not product demonstration. Measured: an 8s clip of a
    workstation renders beautifully and the code on its monitor is decorative
    gibberish — which is fine at a shallow depth of field behind a section, and
    useless as the thing a reader is meant to read. Anything legible is an
    image; `generate` handles those.

    Every keyword here was already supported and unsent. The body was
    `{model_id, prompt}` for as long as this function has existed, which left
    four decisions to the model's defaults:

    - `aspect_ratio` — 16:9 or 9:16, nothing else. A source's video is measured
      full-bleed behind a band or as a portrait rail, and those are different
      shapes; generating 16:9 for both and letting CSS crop is how a portrait
      loop becomes a letterbox.
    - `resolution` — defaulted to 720p. A full-bleed background at 720p on a
      1440 viewport is upscaled by the browser.
    - `negative_prompt` — the "nothing in frame is meant to be read" rules were
      prose inside the positive prompt, where they compete with the description
      instead of constraining it.
    - `generate_audio` — veo returns an AAC track by default and the harness
      shipped it, muted, on every byte a reader downloads.

    What is NOT supported, confirmed by probing the schema: `duration` and
    `loop`. The prompt asks for 8 seconds and a seamless loop and gets neither
    guaranteed, so both are post-processing concerns.
    """
    body: dict = {
        "model_id": VIDEO_MODEL,
        "prompt": prompt,
        "aspect_ratio": VIDEO_SHAPES.get(shape, "16:9"),
        "resolution": resolution,
        "generate_audio": audio,
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    if seed is not None:
        body["seed"] = seed
    return _run("video", body)

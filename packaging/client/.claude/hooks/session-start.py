#!/usr/bin/env python3
"""Runs when a Claude Code session starts in this folder.

Its stdout is injected into Claude's context, not printed to the user. So it
does not say hello itself — it tells Claude to, and hands over the state of the
folder so that the greeting can be accurate rather than generic.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def port() -> str:
    """Same precedence as bin/site: env, then the folder's remembered port."""
    if os.environ.get("SPARROW_PORT"):
        return os.environ["SPARROW_PORT"]
    f = ROOT / ".sparrow" / "port"
    if f.is_file():
        digits = "".join(c for c in f.read_text() if c.isdigit())
        if digits:
            return digits
    return "8000"


PORT = port()


def engine() -> str:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2):
            return f"running on port {PORT}"
    except (urllib.error.URLError, OSError):
        return f"not running (start it with: bin/site up) — port {PORT}"


def projects() -> list[str]:
    out = []
    for d in sorted((ROOT / "projects").glob("*/")):
        bb = d / "blackboard.json"
        if not bb.is_file():
            continue
        try:
            data = json.loads(bb.read_text())
        except Exception:
            continue
        name = (data.get("brief") or {}).get("product_name") or ""
        stage = data.get("stage") or "?"
        out.append(f"  - {d.name}  (stage: {stage}{', ' + name if name else ''})")
    return out


existing = projects()
state = (
    "Sites already started in this folder:\n" + "\n".join(existing)
    + "\n\nOpen by asking whether they want to carry on with one of those or "
      "start something new."
    if existing else
    "No sites have been started here yet. This is a first run."
)

context = f"""SPARROW SITE BUILDER — session start.

You are here to build this person's website. CLAUDE.md is the whole brief; follow it.

Engine: {engine()}

{state}

Your first message this session must be the greeting from CLAUDE.md and nothing
else. Do not run commands, do not explore the repo, do not create anything before
there is a brief. If the user's first message already describes their business,
skip the greeting and go straight to the interview.
"""

print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": context,
}}))

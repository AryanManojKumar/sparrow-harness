"""Structured, traceable logging for the whole harness.

Three consumers, one format:

- a human watching a run, who needs readable lines on a console
- a frontend, which needs the same events over SSE
- whoever is debugging a run next week, who needs the record to still exist

So everything is written as JSONL — one self-describing event per line, appended
to a per-project file and a global one. JSONL because it is greppable with the
tools already on the machine, streamable without a parser, and loadable into
anything later without a migration.

WHAT IS ACTUALLY WORTH RECORDING. Model calls are the expensive, non-deterministic
part, and they are what you cannot reconstruct afterwards. Every one records its
agent, tier, model, token counts split by cached and fresh, cost, duration, and a
hash of the exact prompt — so two runs that diverged can be diffed down to the
call where they stopped matching. Prompt and response text is stored too, capped,
behind SPARROW_LOG_PROMPTS, because it is bulky and sometimes sensitive.

Correlation is by `trace_id` (one per run) and `span_id` (one per call), carried
in a contextvar so an agent deep in the stack does not have to be handed them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = ROOT / "logs"
LOG_PROMPTS = os.environ.get("SPARROW_LOG_PROMPTS", "").lower() in {"1", "true", "yes"}
PROMPT_CAP = int(os.environ.get("SPARROW_LOG_PROMPT_CAP", "4000"))

_trace: ContextVar[str | None] = ContextVar("sparrow_trace", default=None)
_project: ContextVar[str | None] = ContextVar("sparrow_project", default=None)
_stage: ContextVar[str | None] = ContextVar("sparrow_stage", default=None)


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def current_trace() -> str | None:
    return _trace.get()


def bind(project: str, trace_id: str | None = None,
         stage: str | None = None) -> str:
    """Bind the labels with no token and no unwind. Safe across contexts.

    A ContextVar token may only be reset in the Context that created it, and
    two things here routinely cross one:

      * `Run.advance` is a generator. Its `with` body spans every `yield`, so
        the tokens are created on the first `next()` and unwound whenever the
        consumer happens to close it — often a different Context under an SSE
        response.
      * ASGI middleware returns before a StreamingResponse body runs, so a
        `with` around `call_next` has already exited by the time the run
        streams anything.

    Both produced `Token ... was created in a different Context` in a live run.
    These vars are labels on log lines: the correct behaviour when a context is
    re-entered is to overwrite them, which is exactly what a plain `set` does.
    """
    tid = trace_id or _trace.get() or new_trace_id()
    _trace.set(tid)
    _project.set(project)
    if stage is not None:
        _stage.set(stage)
    return tid


@contextmanager
def trace(project: str, trace_id: str | None = None, stage: str | None = None) -> Iterator[str]:
    """Bind a project (and optionally a stage) for everything logged inside.

    Use `bind` instead wherever the scope can span a `yield` or an `await` that
    hands control to another Context; the unwind here is best-effort for that
    reason and never raises.
    """
    tid = trace_id or _trace.get() or new_trace_id()
    tokens = [_trace.set(tid), _project.set(project)]
    if stage is not None:
        tokens.append(_stage.set(stage))
    try:
        yield tid
    finally:
        for t in reversed(tokens):
            try:
                t.var.reset(t)
            except ValueError:
                # Reset in a foreign Context. The label is per-context anyway,
                # so leaving it is correct and raising here would replace a
                # real error with a bookkeeping one.
                pass


@contextmanager
def stage(name: str) -> Iterator[None]:
    tok = _stage.set(name)
    try:
        yield
    finally:
        _stage.reset(tok)


@dataclass
class Event:
    ts: float
    kind: str                      # http | stage | llm | image | tool | diff | error
    message: str
    trace_id: str | None = None
    project: str | None = None
    stage: str | None = None
    span_id: str | None = None
    duration_ms: int | None = None
    cost: float | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def line(self) -> str:
        return json.dumps({k: v for k, v in asdict(self).items() if v not in (None, {})},
                          separators=(",", ":"), default=str)


# ------------------------------------------------------------------- sinks

_console = logging.getLogger("sparrow")
if not _console.handlers:
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    _console.addHandler(h)
    _console.setLevel(os.environ.get("SPARROW_LOG_LEVEL", "INFO"))


def _append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def emit(ev: Event, *, console: str | None = None) -> Event:
    """Write one event everywhere it belongs.

    Per-project first: when something goes wrong, the question is always "what
    happened on THAT run", and grepping one file beats filtering a global one.
    """
    ev.trace_id = ev.trace_id or _trace.get()
    ev.project = ev.project or _project.get()
    ev.stage = ev.stage or _stage.get()
    line = ev.line()
    _append(LOG_DIR / "sparrow.jsonl", line)
    if ev.project:
        _append(ROOT / "projects" / ev.project / "logs" / "run.jsonl", line)
    if console is not None:
        _console.info(console)
    return ev


# ------------------------------------------------------------------ helpers

def _digest(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", "replace"))
    return h.hexdigest()[:12]


def _clip(text: str) -> str:
    return text if len(text) <= PROMPT_CAP else text[:PROMPT_CAP] + f"…[+{len(text)-PROMPT_CAP}]"


def log_llm(
    *, agent: str, provider: str, tier: str, model: str, system: str, user: str,
    text: str, input_tokens: int, cached_tokens: int, output_tokens: int,
    cost: float, duration_ms: int, images: int = 0, error: str | None = None,
) -> Event:
    """One model call. The unit of spend and the unit of non-determinism."""
    data: dict[str, Any] = {
        "agent": agent, "provider": provider, "tier": tier, "model": model,
        "tokens": {"input": input_tokens, "cached": cached_tokens,
                   "output": output_tokens,
                   "cache_hit": round(cached_tokens / max(input_tokens + cached_tokens, 1), 3)},
        "prompt_sha": _digest(system, user),
        "images": images,
    }
    if error:
        data["error"] = error
    if LOG_PROMPTS:
        data["prompt"] = {"system": _clip(system), "user": _clip(user)}
        data["response"] = _clip(text)
    total = input_tokens + cached_tokens
    return emit(
        Event(time.time(), "error" if error else "llm",
              f"{agent} → {model}", duration_ms=duration_ms, cost=cost,
              span_id=uuid.uuid4().hex[:8], data=data),
        console=(f"  llm   {agent:<16} {model:<18} {total:>6,} in "
                 f"({data['tokens']['cache_hit']:.0%} cached) {output_tokens:>5,} out  "
                 f"${cost:.4f}  {duration_ms}ms" + (f"  ERROR {error}" if error else "")),
    )


def log_stage(name: str, kind: str, message: str, cost: float = 0.0, **data: Any) -> Event:
    return emit(Event(time.time(), "stage", message, stage=name, cost=cost or None,
                      data=data),
                console=f"  {kind:<9} {name:<14} {message}"
                        + (f"  ${cost:.4f}" if cost else ""))


def log_http(method: str, path: str, status: int, duration_ms: int, **data: Any) -> Event:
    return emit(Event(time.time(), "http", f"{method} {path} {status}",
                      duration_ms=duration_ms, data=data),
                console=f"  http      {method:<6} {path:<44} {status} {duration_ms}ms")


def log_error(where: str, exc: BaseException, **data: Any) -> Event:
    return emit(Event(time.time(), "error", f"{where}: {type(exc).__name__}: {exc}",
                      data=data),
                console=f"  ERROR     {where}: {type(exc).__name__}: {exc}")


# ------------------------------------------------------------------- reading

def read_run(project: str, kinds: set[str] | None = None, limit: int = 500) -> list[dict]:
    """Replay a project's log. The trace half of 'store it and trace it'."""
    p = ROOT / "projects" / project / "logs" / "run.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if kinds and ev.get("kind") not in kinds:
            continue
        out.append(ev)
    return out[-limit:]


def summarise_run(project: str) -> dict[str, Any]:
    """What a run cost and where it went — the question asked most often."""
    events = read_run(project, limit=100_000)
    llm = [e for e in events if e.get("kind") == "llm"]
    by_agent: dict[str, dict[str, float]] = {}
    for e in llm:
        a = e.get("data", {}).get("agent", "?")
        row = by_agent.setdefault(a, {"calls": 0, "cost": 0.0, "in": 0, "out": 0})
        row["calls"] += 1
        row["cost"] += e.get("cost") or 0.0
        t = e.get("data", {}).get("tokens", {})
        row["in"] += t.get("input", 0) + t.get("cached", 0)
        row["out"] += t.get("output", 0)
    return {
        "project": project,
        "events": len(events),
        "llm_calls": len(llm),
        "total_cost": round(sum(e.get("cost") or 0.0 for e in events), 4),
        "wall_seconds": round((events[-1]["ts"] - events[0]["ts"]) if events else 0, 1),
        "by_agent": {k: {**v, "cost": round(v["cost"], 4)} for k, v in
                     sorted(by_agent.items(), key=lambda kv: -kv[1]["cost"])},
    }

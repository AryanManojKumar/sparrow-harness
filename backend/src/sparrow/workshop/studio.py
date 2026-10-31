"""Agent sessions and builds, both jailed.

One DeepSeek Harness runtime per project, started on the first turn and kept
warm until it idles out. Its session is persisted in the project's dsh-home and
resumed across restarts, so the agent remembers what it changed an hour ago.

A turn streams small events — which tool ran on which file — and ends with the
agent's own summary, the files that changed, and a checkpoint id. Translating
those into words a business owner reads is the office's job, not this one: the
workshop reports facts.

The runtime is configured by a profile patch written here, not by the user:
it routes the model through the office's gateway and removes the tools a
website editor has no business holding — `plugin_manager` can install code
into the runtime itself, and the scheduler starts work nobody asked for.
"""

from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterator

from sparrow.workshop import look, store
from sparrow.workshop.config import WorkshopConfig
from sparrow.workshop.jail import JailMounts, jail_argv, launcher_script

# The route and model names the agent asks the gateway for. Labels only: the
# gateway maps "studio" to whichever model the office is configured to use.
ROUTE = "office"
MODEL = "studio"
SESSION = "studio"
TOKEN_ENV = "STUDIO_LLM_TOKEN"
BUILD_TIMEOUT = 300

PATCH = """\
# Written by sparrow.workshop.studio — regenerated on every workshop start.
- id: llm-pi-ai
  config:
    providers:
      {route}:
        displayName: Studio
        api: openai-completions
        baseURL: {llm_url}
        apiKeyEnv: {token_env}
        models:
          - id: {model}
            name: Studio
            input: [text, image]
            contextWindow: 400000
            maxTokens: 64000

# The workspace has no .git (checkpoints live outside it), so the project root
# is marked by package.json: AGENTS.md at the workspace root is always found.
- id: agent-instructions
  config:
    maxBytes: 65536
    projectRootMarkers: [package.json]

- id: tool-plugin-manager
  disabled: true
- id: tool-schedule
  disabled: true
- id: schedule
  disabled: true
"""


def runtime_paths() -> tuple[Path, Path]:
    """(the runtime package directory, the runtime executable)."""
    from deepseek_harness_runtime import bundled_package_dir, bundled_runtime_path
    return Path(bundled_package_dir()), Path(bundled_runtime_path())


def write_patch(cfg: WorkshopConfig) -> Path:
    path = cfg.root / "_config" / "studio.patch.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PATCH.format(route=ROUTE, llm_url=cfg.llm_url,
                                 token_env=TOKEN_ENV, model=MODEL))
    return path


def mounts(cfg: WorkshopConfig, proj: store.Project, *readonly: Path) -> JailMounts:
    return JailMounts(workspace=proj.workspace, home=proj.home, node=cfg.node,
                      node_modules=cfg.deps / "node_modules", readonly=readonly)


# ── builds ──────────────────────────────────────────────────────────────────

def _deps(pkg: Path) -> dict:
    d = json.loads(pkg.read_text())
    return {**d.get("dependencies", {}), **d.get("devDependencies", {})}


def build(cfg: WorkshopConfig, proj: store.Project) -> dict:
    """`next build` in the jail. Returns {ok, seconds, log}.

    Refuses a workspace whose dependencies differ from the shared install:
    node_modules is the scaffold's, so a package the agent added would be
    missing at build time and fail confusingly three screens down the log.
    """
    if _deps(proj.workspace / "package.json") != _deps(cfg.deps / "package.json"):
        return {"ok": False, "seconds": 0, "log":
                "package.json dependencies differ from the shared install; "
                "adding packages is not supported yet"}
    argv = jail_argv(mounts(cfg, proj),
                     [str(proj.workspace / "node_modules" / ".bin" / "next"), "build"], {})
    t0 = time.time()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "seconds": BUILD_TIMEOUT, "log": "build timed out"}
    log = (r.stdout + r.stderr)[-6000:]
    return {"ok": r.returncode == 0, "seconds": round(time.time() - t0, 1), "log": log}


# ── agent sessions ──────────────────────────────────────────────────────────

REPAIR = """\
The production build failed after your change. Fix the cause — do not delete \
the feature or work around the error — then run ./node_modules/.bin/next build \
again until it passes. Reply with one plain sentence.

Build output (tail):
{log}
"""

LOOKS_RIGHT = "LOOKS RIGHT"
LOOK = """\
Your change builds. These are screenshots of the built pages you affected \
({pages}), at desktop width, top to bottom. Check them as the owner will see \
them: text that is invisible or unreadable against its background, overlapping \
or clipped elements, missing or broken images, layout that does not match the \
rest of the site, anything that does not do what was asked. If something is \
wrong, fix it and rebuild, then reply with one plain sentence about what you \
polished. If everything is right, change nothing and reply exactly: LOOKS RIGHT
"""


class Busy(RuntimeError):
    pass


@dataclass
class _Live:
    harness: object
    session: object
    token: str
    last_used: float = field(default_factory=time.time)


# Tools that are the agent's own bookkeeping rather than work on the site: their
# effect is reported through other events (todo/write) or not at all.
_QUIET_TOOLS = {"todo_write", "create_goal", "get_goal", "update_goal", "working_directory"}
_LINE = re.compile(r"^\s*\d+: ", re.M)


class Translator:
    """Runtime notifications → the workshop's activity events, for one agent run.

    The owner's UI shows the agent working the way a coding agent's terminal
    does — each tool on what it touched, the result underneath, the to-do list
    as it changes — so these events carry that, and nothing more:

        tool         {id, tool, target, detail}     a call started
        tool_result  {id, ok, summary}              how it ended, one or a few lines
        todos        {items: [{content, status}]}   the agent's plan, whole, each time
        note         {text}                         words the agent wrote beside its tools

    Every absolute path is cut back to workspace-relative before it leaves:
    the jail's layout is the workshop's business, not the browser's.
    Results do not name their tool, so calls are remembered by id.
    """

    def __init__(self, workspace: Path) -> None:
        self.ws = str(workspace)
        self.calls: dict[str, str] = {}

    def _rel(self, text: str) -> str:
        text = text.replace(self.ws + "/", "")
        return text.replace(self.ws, ".")

    def _call(self, data: dict) -> dict | None:
        name, cid = data.get("name") or "", data.get("callId") or ""
        self.calls[cid] = name
        if name in _QUIET_TOOLS:
            return None
        raw = data.get("arguments")
        try:
            args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except json.JSONDecodeError:
            args = {}
        target, detail = "", ""
        for key in ("file_path", "path", "pattern"):
            if isinstance(args.get(key), str) and args[key]:
                target = self._rel(args[key])
                break
        if name == "bash":
            target = self._rel(str(args.get("command", "")))[:240]
            detail = str(args.get("description", ""))[:160]
        elif name == "edit":
            old = str(args.get("old_string", "")).count("\n") + 1
            new = str(args.get("new_string", "")).count("\n") + 1
            detail = f"+{new} −{old}"
        elif name == "write":
            detail = f"{str(args.get('content', '')).count(chr(10)) + 1} lines"
        elif name == "grep" and args.get("path"):
            detail = f"in {self._rel(str(args['path']))}"
        return {"kind": "tool", "id": cid, "tool": name, "target": target[:240], "detail": detail}

    def _result(self, data: dict) -> dict | None:
        msg = data.get("message") or data
        cid = msg.get("toolCallId") or (msg.get("source") or {}).get("callId") or ""
        name = self.calls.get(cid, "")
        if name in _QUIET_TOOLS:
            return None
        text = "\n".join(b.get("text", "") for b in msg.get("content") or []
                         if b.get("type") == "text")
        text = self._rel(text).strip()
        ok = not msg.get("isError")
        if not ok:
            summary = text.splitlines()[0][:240] if text else "failed"
        elif name == "read":
            n = len(_LINE.findall(text))
            summary = f"{n} lines" if n else "read"
        elif name in ("glob", "grep"):
            rows = [r for r in text.splitlines() if r.strip()]
            summary = f"{len(rows)} {'files' if name == 'glob' else 'matches'}"
        elif name == "bash":
            tail = [r for r in text.splitlines() if r.strip()][-6:]
            summary = "\n".join(tail)[-600:] or "(no output)"
        elif name in ("edit", "write"):
            summary = "applied"
        else:
            summary = text.splitlines()[0][:200] if text else "done"
        return {"kind": "tool_result", "id": cid, "ok": ok, "summary": summary}

    def __call__(self, payload: dict) -> dict | None:
        ev = payload.get("event") or {}
        data = ev.get("data") or {}
        kind = ev.get("type")
        if kind == "tool/call":
            return self._call(data)
        if kind == "tool/result":
            return self._result(data)
        if kind == "todo/write":
            items = [{"content": str(t.get("content", ""))[:200], "status": t.get("status", "pending")}
                     for t in data.get("todos") or []]
            return {"kind": "todos", "items": items}
        if kind == "assistant/message":
            blocks = (data.get("message") or {}).get("content") or []
            # Text beside a tool call is narration; text alone is the final
            # answer, which arrives as the turn's reply instead.
            if any(b.get("type") == "tool-call" for b in blocks):
                text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
                if text:
                    return {"kind": "note", "text": self._rel(text)[:800]}
        return None


class Studio:
    def __init__(self, cfg: WorkshopConfig) -> None:
        self.cfg = cfg
        self.patch = write_patch(cfg)
        self.runtime_dir, self.runtime = runtime_paths()
        self._live: dict[str, _Live] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        threading.Thread(target=self._reap, daemon=True).start()

    def _lock(self, pid: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(pid, threading.Lock())

    def _launch(self, proj: store.Project, token: str) -> _Live:
        from deepseek_harness import DeepSeekHarness

        m = mounts(self.cfg, proj, self.runtime_dir, self.patch.parent)
        # The runtime re-renders cordis.yml on every boot, but the two files it
        # renders FROM — the persistent user patch and the plugin manifest — it
        # only writes on first boot. Read-only after that, so nothing in the
        # jail can re-enable the plugin installer or add a plugin for next time.
        profile = proj.home / "profiles" / "sdk"
        locked = tuple(f for f in (profile / "cordis.patch.yml", profile / "package.json")
                       if f.is_file())
        # The dossier is the office's description of the site; the agent reads
        # it and must not be able to rewrite what it is told.
        if proj.dossier.is_file():
            locked += (proj.dossier,)
        if locked:
            m = replace(m, readonly_over=locked)
        proj.launcher.write_text(launcher_script(m, self.runtime, (TOKEN_ENV,)))
        proj.launcher.chmod(0o700)
        h = DeepSeekHarness(
            dsh_home=str(proj.home), cwd=str(proj.workspace), dsh_bin=str(proj.launcher),
            provider=ROUTE, model=MODEL, patches=(str(self.patch),),
            env={TOKEN_ENV: token}, initialize_timeout_seconds=120)
        try:
            s = h.resume_session(SESSION)
        except Exception:
            s = h.start_session(SESSION)
        return _Live(h, s, token)

    def _close(self, pid: str) -> None:
        live = self._live.pop(pid, None)
        if live is not None:
            try:
                live.harness.close()
            except Exception:
                pass

    def _reap(self) -> None:
        while True:
            time.sleep(60)
            for pid, live in list(self._live.items()):
                lock = self._lock(pid)
                if time.time() - live.last_used > self.cfg.idle_seconds and lock.acquire(False):
                    try:
                        self._close(pid)
                    finally:
                        lock.release()

    def busy(self, pid: str) -> bool:
        return self._lock(pid).locked()

    def _run(self, live: _Live, proj: store.Project, prompt, emit) -> str:
        translate = Translator(proj.workspace)

        def on_n(n) -> None:
            e = translate(n.payload)
            if e is not None:
                emit(e)

        r = live.session.run(prompt, on_notification=on_n)
        live.last_used = time.time()
        return r.final_response or ""

    def _settle(self, live: _Live, proj: store.Project, emit, repairs: int) -> dict:
        """Build; on failure hand the log back to the agent, up to `repairs` times."""
        emit({"kind": "status", "text": "checking the build"})
        result = build(self.cfg, proj)
        for _ in range(repairs):
            if result["ok"]:
                break
            emit({"kind": "status", "text": "fixing a build error"})
            self._run(live, proj, REPAIR.format(log=result["log"][-3500:]), emit)
            emit({"kind": "status", "text": "checking the build"})
            result = build(self.cfg, proj)
        return result

    def _loop(self, live: _Live, proj: store.Project, message: str, emit) -> dict:
        """edit → build (→ repair) → look (→ polish → build) → one checkpoint.

        Whatever the user is shown has built. A change that never builds is
        thrown away without a trace — it was never on the page, so there is
        nothing to undo — and the user is told that plainly.
        """
        t0 = time.time()
        base = store.head(proj)
        reply = self._run(live, proj, message, emit)
        if not store.files_since(proj, base):
            return {"kind": "done", "reply": reply, "changed": [], "checkpoint": None,
                    "reverted": False, "seconds": round(time.time() - t0, 1)}

        built = self._settle(live, proj, emit, repairs=2)
        if not built["ok"]:
            emit({"kind": "status", "text": "undoing a change that broke the site"})
            store.reset_to(proj, base)
            build(self.cfg, proj)  # put the preview back to the last good site
            return {"kind": "done", "reply": reply, "changed": [], "checkpoint": None,
                    "reverted": True, "build_log": built["log"][-1500:],
                    "seconds": round(time.time() - t0, 1)}
        good = store.checkpoint(proj, "studio: built") or base

        try:
            emit({"kind": "status", "text": "looking at the result"})
            shots = look.shoot(proj.export, look.base_path(proj.workspace),
                               look.routes_for(store.files_since(proj, base)))
        except Exception as e:  # a missing browser must not cost the user their change
            emit({"kind": "status", "text": f"could not take screenshots ({type(e).__name__})"})
            shots = []
        if shots:
            blocks: list[dict] = [{"type": "text", "text": LOOK.format(
                pages=", ".join(sorted({s["route"] for s in shots})))}]
            for s in shots:
                blocks.append({"type": "text", "text": f"{s['route']} — part {s['part']} of {s['of']}"})
                blocks.append({"type": "image", "data": s["data"], "mimeType": "image/jpeg"})
            note = self._run(live, proj, blocks, emit)
            if store.files_since(proj, good):
                emit({"kind": "status", "text": "polishing"})
                polished = self._settle(live, proj, emit, repairs=1)
                if polished["ok"]:
                    if note.strip() and LOOKS_RIGHT not in note:
                        reply = f"{reply}\n\n{note}".strip()
                else:
                    store.reset_to(proj, good)
                    build(self.cfg, proj)

        changed = store.files_since(proj, base)
        title = message.strip().splitlines()[0][:120] or "Studio change"
        cid = store.squash_since(proj, base, title)
        return {"kind": "done", "reply": reply, "changed": changed, "checkpoint": cid,
                "reverted": False, "screenshots": len(shots),
                "seconds": round(time.time() - t0, 1)}

    def turn(self, proj: store.Project, message: str, token: str) -> Iterator[dict]:
        """Run one user request. Yields events; the last is `done` or `error`.

        The turn runs on its own thread and finishes even if the caller stops
        listening — the work is paid for, and the checkpoint at the end is what
        makes it undoable.
        """
        lock = self._lock(proj.pid)
        if not lock.acquire(False):
            raise Busy(proj.pid)
        q: queue.Queue = queue.Queue()

        def work() -> None:
            try:
                live = self._live.get(proj.pid)
                if live is not None and live.token != token:
                    self._close(proj.pid)  # a new token means a fresh runtime
                    live = None
                if live is None:
                    q.put({"kind": "status", "text": "starting"})
                    live = self._live[proj.pid] = self._launch(proj, token)
                q.put(self._loop(live, proj, message, q.put))
            except Exception as e:  # the runtime died or the gateway refused
                self._close(proj.pid)
                q.put({"kind": "error", "text": f"{type(e).__name__}: {e}"[:800]})
            finally:
                lock.release()
                q.put(None)

        threading.Thread(target=work, daemon=True).start()
        while (e := q.get()) is not None:
            yield e

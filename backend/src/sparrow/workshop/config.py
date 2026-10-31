"""Workshop settings, read from the environment once.

Deliberately NOT read from `backend/.env`: that file holds the office's provider
keys, and a workshop process that loads it has defeated the point of being a
separate process. The workshop's own settings live in `backend/workshop.env`
(or the real environment), and none of them is a provider credential.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[4]


def _node_dir() -> Path | None:
    node = shutil.which("node")
    return Path(node).resolve().parent.parent if node else None


@dataclass(frozen=True)
class WorkshopConfig:
    # Where projects live: <root>/<pid>/{workspace,dsh-home,checkpoints.git}.
    root: Path
    # Shared secret the office presents on every call. Required: an
    # unauthenticated workshop is a remote code execution endpoint.
    token: str
    # A scaffold checkout WITH node_modules. Mounted read-only into every jail
    # as the project's node_modules — the stack is fixed (CLAUDE.md §9), so one
    # install serves every project and nothing is installed at runtime.
    deps: Path
    # A Node install prefix (contains bin/node). Mounted read-only.
    node: Path
    # The office's LLM gateway, as the agent inside the jail will reach it.
    # The workshop never names a real model: it asks for "studio" and the
    # gateway decides what that means (`sparrow.gateway`).
    llm_url: str
    # Seconds an idle agent runtime is kept warm before it is closed.
    idle_seconds: int = 900

    @classmethod
    def load(cls) -> "WorkshopConfig":
        env = {**dotenv_values(ROOT / "backend" / "workshop.env"), **os.environ}
        token = (env.get("WORKSHOP_TOKEN") or "").strip()
        if len(token) < 24:
            raise RuntimeError(
                "WORKSHOP_TOKEN must be set (24+ characters) — the workshop runs "
                "model-written code and must not accept unauthenticated calls")
        node = Path(env["WORKSHOP_NODE"]) if env.get("WORKSHOP_NODE") else _node_dir()
        if node is None or not (node / "bin" / "node").exists():
            raise RuntimeError("WORKSHOP_NODE must point at a Node prefix containing bin/node")
        deps = Path(env.get("WORKSHOP_DEPS") or ROOT / "scaffold")
        if not (deps / "node_modules").is_dir():
            raise RuntimeError(f"WORKSHOP_DEPS={deps} has no node_modules — run pnpm install there")
        return cls(
            root=Path(env.get("WORKSHOP_ROOT") or ROOT / "workshop-data").resolve(),
            token=token,
            deps=deps.resolve(),
            node=node.resolve(),
            llm_url=env.get("WORKSHOP_LLM_URL") or "http://127.0.0.1:8001/llm/v1",
            idle_seconds=int(env.get("WORKSHOP_IDLE_SECONDS") or 900),
        )

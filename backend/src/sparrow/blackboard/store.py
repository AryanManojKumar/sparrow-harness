"""Versioned blackboard store.

One write path: `apply`. Agents never mutate state — they return an RFC 6902
patch, the store validates it against the schema, and rejects with a reason the
agent can act on. Backed by a JSON file for now; the shape is deliberately the
one Postgres JSONB will take.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import jsonpatch
from pydantic import ValidationError

from sparrow.blackboard.schema import Blackboard, Decision


@dataclass(frozen=True)
class Rejected:
    """Returned to the proposing agent verbatim, so it can adapt."""

    reason: str


@dataclass(frozen=True)
class Applied:
    version: int


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ read

    def load(self) -> Blackboard:
        if not self.path.exists():
            raise FileNotFoundError(f"no blackboard at {self.path}")
        return Blackboard.model_validate_json(self.path.read_text())

    def init(self, project_id: str) -> Blackboard:
        bb = Blackboard(project_id=project_id)
        self._write(bb)
        return bb

    # ----------------------------------------------------------------- write

    def apply(
        self,
        patch: list[dict],
        *,
        agent: str,
        summary: str,
        expect_version: int | None = None,
    ) -> Applied | Rejected:
        """Apply an RFC 6902 patch, or reject it with a reason.

        Rejection is not an exception — the caller is a model, and a reason it
        can read is worth more than a stack trace it cannot.
        """
        current = self.load()

        if expect_version is not None and expect_version != current.version:
            return Rejected(
                f"stale patch: built against version {expect_version}, "
                f"blackboard is at {current.version}. Re-read and re-propose."
            )

        doc = current.model_dump(mode="json")
        try:
            patched = jsonpatch.apply_patch(doc, patch)
        except jsonpatch.JsonPatchException as e:
            return Rejected(f"patch could not be applied: {e}")
        except jsonpatch.JsonPointerException as e:
            return Rejected(f"patch targets a path that does not exist: {e}")

        try:
            bb = Blackboard.model_validate(patched)
        except ValidationError as e:
            return Rejected(f"patch produces an invalid blackboard: {e.errors()}")

        bb.version = current.version + 1
        bb.decisions.append(Decision(
            id=f"d{len(bb.decisions) + 1:04d}", agent=agent, summary=summary,
        ))
        self._write(bb)
        return Applied(bb.version)

    def _write(self, bb: Blackboard) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(bb.model_dump_json(indent=2))
        tmp.replace(self.path)  # atomic

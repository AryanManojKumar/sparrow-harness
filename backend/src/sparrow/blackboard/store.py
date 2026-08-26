"""Versioned blackboard store.

One write path: `apply`. Agents never mutate state — they return an RFC 6902
patch, the store validates it against the schema, and rejects with a reason the
agent can act on. Backed by a JSON file for now; the shape is deliberately the
one Postgres JSONB will take.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import jsonpatch
from pydantic import ValidationError

from sparrow.blackboard.schema import Blackboard, Decision


@dataclass(frozen=True)
class Rejected:
    """Returned to the proposing agent verbatim, so it can adapt.

    Two fields, not one — the shape DeepSeek Harness uses for `GoalBlockReason`.
    `code` is a stable lower-kebab-case classification the orchestrator routes on;
    `message` is prose for a human or a model. One field cannot serve both: a
    string a machine can branch on reads as noise to a business owner, and prose
    a human understands cannot be matched against. This is the concrete answer to
    CLAUDE.md §8 — `contrast_ratio_failed: 3.9` is a routing code, never the thing
    you show someone.
    """

    code: str
    message: str

    @property
    def reason(self) -> str:  # backwards-compatible read
        return self.message


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
        supersedes: str | None = None,
        expect_version: int | None = None,
    ) -> Applied | Rejected:
        """Apply an RFC 6902 patch, or reject it with a reason.

        Rejection is not an exception — the caller is a model, and a reason it
        can read is worth more than a stack trace it cannot.
        """
        current = self.load()

        if expect_version is not None and expect_version != current.version:
            return Rejected("stale-revision", f"stale patch: built against version {expect_version}, "
                f"blackboard is at {current.version}. Re-read and re-propose.")

        doc = current.model_dump(mode="json")
        try:
            patched = jsonpatch.apply_patch(doc, patch)
        except jsonpatch.JsonPatchException as e:
            return Rejected("patch-inapplicable", f"patch could not be applied: {e}")
        except jsonpatch.JsonPointerException as e:
            return Rejected("unknown-path", f"patch targets a path that does not exist: {e}")

        try:
            bb = Blackboard.model_validate(patched)
        except ValidationError as e:
            return Rejected("schema-violation", f"patch produces an invalid blackboard: {e.errors()}")

        bb.version = current.version + 1
        bb.decisions.append(Decision(
            id=f"d{len(bb.decisions) + 1:04d}", agent=agent, summary=summary,
            supersedes=supersedes,
        ))
        self._write(bb)
        return Applied(bb.version)

    def set_stage(self, stage: str) -> None:
        """Move the run pointer. Deliberately not an `apply`.

        Every stage transition going through `apply` would append a Decision
        per step — eleven rows of "now at build" that bury the decisions a human
        would actually want to read. The pointer is bookkeeping, not a decision;
        the decisions are what happened INSIDE each stage.
        """
        bb = self.load()
        if bb.stage == stage:
            return
        bb.stage = stage
        self._write(bb)

    def _write(self, bb: Blackboard) -> None:
        """Serialise, flush, rename. A half-written blackboard loses the project.

        Three separate failures are being defended against, and only the third
        was already covered:

        1. SERIALISATION THROWS. `model_dump_json` runs before anything touches
           the filesystem, so a model that will not serialise leaves the file on
           disk exactly as it was rather than truncated to nothing.
        2. TWO WRITERS SHARE ONE SCRATCH FILE. The temp name was
           `blackboard.tmp` — one fixed name for every writer of this project.
           Two processes (an SSE advance the API kept alive plus a CLI command,
           which is reachable today) interleave their writes into that one file
           and then both rename it into place, so the surviving file is halves of
           two different blackboards and parses as neither. The pid makes each
           writer's scratch file its own; the rename is still atomic, so the
           worst case degrades to a lost update rather than a corrupt file.
        3. THE RENAME IS NOT ATOMIC. It is, on the same filesystem — which is why
           the temp file is written beside the target and never in /tmp.

        The fsync is the difference between "the rename is atomic" and "the
        renamed file has contents": without it a crash after the rename can leave
        a correctly-named, zero-length file, which is the one outcome this whole
        function exists to prevent.
        """
        body = bb.model_dump_json(indent=2)
        tmp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        try:
            with open(tmp, "w") as fh:
                fh.write(body)
                fh.flush()
                os.fsync(fh.fileno())
            tmp.replace(self.path)  # atomic within the directory
        finally:
            # A crash between write and rename leaves scratch behind; the next
            # successful write must not inherit it as a sibling nobody reads.
            if tmp.exists():
                tmp.unlink(missing_ok=True)

"""The orchestrator.

Not an agent. It sequences the run, applies or rejects every diff, counts rounds,
and stops at the three gates. Until now the pipeline was nine CLI commands run by
hand in the right order — which is how `page.tsx` went uncomposed through two
whole experiments without anyone noticing.

CLAUDE.md §8: gates are few and each one is a decision only a human holds.
Brief, design direction, whose imagery, full preview. Everything between them
runs without asking.

The asset gate is the fourth, and it is not an approval step — it is the only
point at which the user's REAL material can enter the run. Without it the
curator silently generated every image a blueprint asked for, which makes §2's
differentiator ("real content, not filler") unreachable by construction: the
system had no moment where a file could be handed to it. Provenance had carried
`user_supplied | restyled | generated` from the start and only ever recorded
`generated`, which is what a missing gate looks like in the data.

A run is a state machine rather than a function because a gate is a stop, and a
stop has to survive the process going away. Every transition is written to the
blackboard, so a run resumes from wherever it halted.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Stage(StrEnum):
    """Ordered. `next_stage` walks this list."""

    BRIEF = "brief"                  # brief exists and is approved
    GATE_BRIEF = "gate:brief"        # ── GATE 1
    SOURCES = "sources"              # extract, classify, rank, blueprint
    DESIGN = "design"                # design system + sitemap
    GATE_DESIGN = "gate:design"      # ── GATE 2 — choose between directions
    CONTENT = "content"              # draft the copy; collect the invented facts
    GATE_ASSETS = "gate:assets"      # ── MATERIAL GATE — per image, and per invented fact
    ASSETS = "assets"                # curator
    BUILD = "build"                  # builder, compose, repair
    VERIFY = "verify"                # drift audit + inspector
    GATE_PREVIEW = "gate:preview"    # ── GATE 3
    DONE = "done"


ORDER: list[Stage] = list(Stage)
GATES = {Stage.GATE_BRIEF, Stage.GATE_DESIGN, Stage.GATE_ASSETS, Stage.GATE_PREVIEW}


def next_stage(s: Stage) -> Stage:
    i = ORDER.index(s)
    return ORDER[min(i + 1, len(ORDER) - 1)]


@dataclass
class Event:
    """One line of run progress. The API streams these; the CLI prints them."""

    stage: Stage
    kind: str          # started | progress | blocked | awaiting | done | failed
    message: str
    data: dict = field(default_factory=dict)
    cost: float = 0.0

    def line(self) -> str:
        mark = {"started": "▸", "progress": " ", "awaiting": "⏸",
                "done": "✓", "failed": "✗", "blocked": "!"}.get(self.kind, " ")
        tail = f"  ${self.cost:.4f}" if self.cost else ""
        return f"{mark} {self.stage.value:<14} {self.message}{tail}"


@dataclass
class GateRequest:
    """What the run needs a human to decide, and the concrete options.

    CLAUDE.md §8: escalation is a choice with options, never a dump of failed
    criteria. A business owner can answer "which of these"; nobody can usefully
    answer "is this good".
    """

    gate: Stage
    question: str
    options: list[dict]
    artifacts: list[str] = field(default_factory=list)


class Halt(Exception):
    """Raised to stop the run at a gate. Carries what the human must decide."""

    def __init__(self, request: GateRequest) -> None:
        super().__init__(request.question)
        self.request = request


class Run:
    """Drives one project through the stages.

    Each stage is a callable registered in `steps`. A stage may yield Events as it
    works, and may raise `Halt` to stop for a human. State lives on the blackboard,
    so a halted run is resumable and a crashed one loses at most one stage.
    """

    def __init__(
        self,
        project_id: str,
        root: Path,
        steps: dict[Stage, Callable[["Run"], Iterator[Event]]],
    ) -> None:
        self.project_id = project_id
        self.root = root
        self.steps = steps
        self.stage: Stage = Stage.BRIEF
        self.spent: float = 0.0
        self.pending: GateRequest | None = None
        self.log: list[Event] = []

    # ------------------------------------------------------------------ paths

    @property
    def dir(self) -> Path:
        return self.root / "projects" / self.project_id

    @property
    def blackboard_path(self) -> Path:
        return self.dir / "blackboard.json"

    @property
    def workspace(self) -> Path:
        return self.dir / "workspace"

    # ------------------------------------------------------------------ drive

    def advance(self) -> Iterator[Event]:  # noqa: C901
        """Run stages until a gate, the end, or a failure.

        Deliberately a generator: a run takes minutes, and a caller — CLI or an
        SSE endpoint — needs progress as it happens rather than at the end.
        """
        from sparrow import telemetry

        with telemetry.trace(self.project_id):
            yield from self._advance()

    def _advance(self) -> Iterator[Event]:
        while self.stage is not Stage.DONE:
            if self.stage in GATES and self.pending is not None:
                yield self._emit(Event(self.stage, "awaiting", self.pending.question))
                return

            step = self.steps.get(self.stage)
            if step is None:                     # a gate with nothing pending clears
                self.stage = next_stage(self.stage)
                continue

            yield self._emit(Event(self.stage, "started", f"{self.stage.value} …"))
            try:
                for ev in step(self):
                    self.spent += ev.cost
                    yield self._emit(ev)
            except Halt as h:
                self.pending = h.request
                yield self._emit(Event(self.stage, "awaiting", h.request.question,
                                       {"options": h.request.options,
                                        "artifacts": h.request.artifacts}))
                return
            except Exception as e:               # a stage failing stops the run
                yield self._emit(Event(self.stage, "failed",
                                       f"{type(e).__name__}: {e}"))
                return

            self.stage = next_stage(self.stage)

        yield self._emit(Event(Stage.DONE, "done", f"run complete · ${self.spent:.4f}"))

    def resolve(self, choice: dict) -> None:
        """Answer the open gate and let the run continue."""
        if self.pending is None:
            raise RuntimeError("no gate is open")
        self.pending = None
        self.stage = next_stage(self.stage)
        self.log.append(Event(self.stage, "progress", f"gate resolved: {choice}"))

    def _emit(self, ev: Event) -> Event:
        from sparrow import telemetry

        self.log.append(ev)
        telemetry.log_stage(ev.stage.value, ev.kind, ev.message, ev.cost, **ev.data)
        return ev

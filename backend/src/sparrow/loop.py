"""Round accounting for every capped loop in the harness.

CLAUDE.md §8 caps loops at 3 because critic-refine plateaus at 2-3 iterations and
then oscillates. That cap is easy to state and easy to get wrong, so the counting
lives here rather than in each caller.

Four rules, taken from the goal-round driver in deepseek-ai/deepseek-harness:

1. RESERVE BEFORE WORKING. The round number is taken before the attempt, not
   after it. A crash mid-attempt must not hand back a free retry.

2. A ROUND THAT NEVER RAN DOES NOT COUNT. Their driver: "a reservation rejected
   as stale does not consume the round number." A provider timeout, a stale
   revision, a rejected patch — none of these were an attempt at the problem, so
   none of them should spend the budget meant for attempts at the problem.

3. HUMAN TURNS ARE FREE. Their driver: "human messages do not consume the goal
   cap." When §8 escalates to the user and they answer, that answer must not have
   cost one of the three tries.

4. EVIDENCE BEFORE COMPLETION. Their retained prompt "requires evidence before
   completion, and tells the model to leave the goal active when work remains."
   Nothing here may be marked done on an agent's say-so; `complete()` demands a
   verified fact.

The cap itself is read from durable state, never passed around as a default —
duplicating it is how two call sites end up enforcing different policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Outcome(StrEnum):
    """Why a reserved round ended. Only ATTEMPTED spends budget."""

    ATTEMPTED = "attempted"      # the agent really tried; counts
    INFRA_FAILED = "infra"       # timeout, transport, rejected patch; does not count
    HUMAN = "human"              # a person answered; does not count
    SUPERSEDED = "superseded"    # state moved underneath us; does not count


@dataclass(frozen=True)
class Blocked:
    """Terminal stop. Carries a routing code and a human sentence, never one alone."""

    code: str
    message: str


@dataclass
class Rounds:
    """Round accounting for one thing being attempted — a section, a repair, a page."""

    subject: str
    cap: int
    spent: int = 0
    reserved: bool = False
    closed: bool = False
    history: list[tuple[int, Outcome, str]] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return max(0, self.cap - self.spent)

    @property
    def exhausted(self) -> bool:
        return self.closed or self.spent >= self.cap

    def reserve(self) -> int | Blocked:
        """Take the next round number before the attempt starts."""
        if self.reserved:
            return Blocked("round-already-open",
                           f"a round is already open on {self.subject}")
        if self.exhausted:
            return Blocked(
                "rounds-exhausted",
                f"{self.subject} did not converge in {self.cap} attempts. "
                f"This needs a decision, not another retry.",
            )
        self.reserved = True
        return self.spent + 1

    def settle(self, outcome: Outcome, note: str = "") -> None:
        """Close the open round. Budget moves only for a real attempt."""
        if not self.reserved:
            raise RuntimeError(f"settle() with no open round on {self.subject}")
        self.reserved = False
        n = self.spent + 1
        if outcome is Outcome.ATTEMPTED:
            self.spent = n
        self.history.append((n, outcome, note))

    def complete(self, evidence: str) -> None:
        """Mark done. `evidence` is a verified fact, never an agent's claim."""
        if not evidence.strip():
            raise ValueError(
                f"cannot complete {self.subject} without evidence — "
                "an agent saying it is done is not evidence"
            )
        if self.reserved:
            self.settle(Outcome.ATTEMPTED, f"complete: {evidence}")
        # Closing is not the same as spending. Overwriting `spent` with `cap`
        # made a first-try success report "3/3 attempts".
        self.closed = True

    def summary(self) -> str:
        free = sum(1 for _, o, _ in self.history if o is not Outcome.ATTEMPTED)
        tail = f", {free} not charged" if free else ""
        state = "done" if self.closed else "open"
        return f"{self.subject}: {self.spent}/{self.cap} attempts, {state}{tail}"

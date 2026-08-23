"""Blackboard schema.

The blackboard is the single source of truth. Nothing downstream keeps its own
copy of anything defined here — the CSS token file and the prompt fragments are
both *rendered* from these models (see `sparrow.render.tokens`), never authored
alongside them. Two hand-maintained representations of the same decision is the
bug this schema exists to prevent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- brief


class Brief(BaseModel):
    """Small enough to inject whole, always. Never retrieved, never summarised."""

    category: str
    offering: str
    audience: str
    tone: str
    primary_action: str
    secondary_action: str | None = None


class Constraint(BaseModel):
    """A hard constraint, in the user's own words.

    `text` is verbatim. The librarian may supersede a constraint but may never
    rewrite one — a paraphrased constraint is a different constraint.
    """

    id: str
    text: str
    superseded_by: str | None = None
    recorded_at: datetime = Field(default_factory=_now)


# ------------------------------------------------------------------ design system


class Scale[T](BaseModel):
    """A closed enumeration.

    The drift test (experiments/drift-test-01) measured this directly: rules
    stated as closed sets held across five independent builds, rules stated as
    open scales leaked. Every scale carries its own closure sentence, generated
    from the data so it cannot go stale.
    """

    items: list[T]
    noun: str  # "values", "weights", "steps" — used in the closure sentence

    def closure(self) -> str:
        n = len(self.items)
        return f"{n} {self.noun}. There is no {_ordinal(n + 1)}."


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


class Color(BaseModel):
    """A colour with a NAME, not just a slot.

    open-design's 154 shipped systems all name their colours — "Rausch",
    "Ink Black", "Hairline Gray", "Soft Cloud" — rather than leaving them as
    `--primary`. A named colour is something an agent can reason about and stay
    faithful to; a slot is something it fills.
    """

    token: str          # "primary" -> --primary
    name: str           # "Evidence Green" — what the design agent calls it
    value: str          # oklch(...)
    role: str           # what it is for, injected into the prompt


class TypeStep(BaseModel):
    name: str           # "display", "h2", "eyebrow"
    classes: str        # the exact Tailwind classes
    use: str            # when to reach for it; may say "hero headline ONLY"


class DesignSystem(BaseModel):
    """The design agent's recorded decisions. Vocabulary, never composition.

    The first three fields are what separates a design system from a token dump.
    They exist because a palette and a type scale do not, on their own, stop a
    model producing the same page it would produce for any other brief.
    """

    # What this looks and feels like, in prose. open-design opens every one of its
    # systems this way, and it is what a builder reads to know whether a choice
    # belongs.
    atmosphere: str

    # The single element this page will be remembered by. Anthropic's
    # frontend-design skill: "Spend your boldness in one place." Without a named
    # signature, boldness gets spread evenly and the page reads as templated.
    signature: str

    # 4-8 specific, checkable statements about what makes this system itself.
    key_characteristics: list[str] = Field(default_factory=list)

    colors: list[Color]
    forbidden_hues: list[tuple[int, int]] = Field(default_factory=list)

    # Three roles, not one string. The first run returned "Spline Sans (primary)
    # paired with IBM Plex Mono (evidence metadata)" in a single field, which is
    # readable prose and unloadable as a font. A field that has to be parsed back
    # out is a field with the wrong shape.
    font_display: str            # headings — the characteristic face
    font_body: str               # prose — may equal font_display
    font_mono: str | None = None # optional: code, IDs, timestamps
    font_weights: list[int]
    type_steps: list[TypeStep]

    section_padding: str
    container: str
    grid_gap: str
    inline_gap: str          # added after drift-test-01: agents invented these
    stack_tight: str
    stack_loose: str

    radius_base: str
    radius_card: str
    radius_input: str
    radius_full_allowed: str  # what may legitimately be fully round

    shadow_rest: str
    shadow_hover: str

    imagery_treatment: str
    motion: str

    def color_scale(self) -> Scale[Color]:
        return Scale(items=self.colors, noun="values")

    def weight_scale(self) -> Scale[int]:
        return Scale(items=self.font_weights, noun="weights")

    def type_scale(self) -> Scale[TypeStep]:
        return Scale(items=self.type_steps, noun="steps")


# ----------------------------------------------------------------------- sections


class Ground(StrEnum):
    """Page vs. muted background.

    Owned by `sitemap`, not by the builder. In drift-test-01 two adjacent
    sections independently chose `muted` and merged into one grey block that
    neither builder could have seen.
    """

    PAGE = "page"
    MUTED = "muted"


class BuildStatus(StrEnum):
    PENDING = "pending"
    BUILT = "built"
    DEFECTIVE = "defective"


class Section(BaseModel):
    id: str
    order: int
    blueprint_id: str
    target_path: str
    component_name: str
    ground: Ground = Ground.PAGE
    status: BuildStatus = BuildStatus.PENDING
    attempts: int = 0
    defects: list[str] = Field(default_factory=list)


class Blueprint(BaseModel):
    """A section's structural spec.

    `slots` and `assets` are separate because two different agents consume them.
    The builder fills slots with copy; `curator` produces assets. Collapsed into
    one list, the blueprinter read "slots" as "image slots" — a hero came back
    with none at all, because it has no imagery.
    """

    id: str
    purpose: str
    slots: list[str]                                  # content the builder writes
    assets: list[str] = Field(default_factory=list)   # imagery curator produces
    structure: str


# -------------------------------------------------------------------- blackboard


class Decision(BaseModel):
    id: str
    agent: str
    summary: str
    supersedes: str | None = None
    at: datetime = Field(default_factory=_now)


class Blackboard(BaseModel):
    project_id: str
    version: int = 0
    brief: Brief | None = None
    constraints: list[Constraint] = Field(default_factory=list)
    design_system: DesignSystem | None = None
    sections: list[Section] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    decisions: list[Decision] = Field(default_factory=list)

    def active_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.superseded_by is None]

    def next_pending(self) -> Section | None:
        pending = [s for s in self.sections if s.status is BuildStatus.PENDING]
        return min(pending, key=lambda s: s.order) if pending else None

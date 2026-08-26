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

    # The one fact every section must agree on. Without it, nine blind builders
    # each invent a plausible name and the page ships with a different product
    # in the nav than in the footer — observed as LedgerRoute vs Railform on the
    # same page. It is not decoration; it is the thing that makes the sections
    # look like one site.
    product_name: str = ""
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


class Provenance(StrEnum):
    """Where an asset came from. Decides what may be claimed about it.

    USER_SUPPLIED — their own file, untouched beyond the PII scrub, cropping and
                    resizing. Scrubbing is not a provenance: a scrubbed upload is
                    still a picture of their real product, and it can be either
                    restyled or shipped as-is. `Asset.scrubbed` records it.
    RESTYLED      — their file, restyled to the design system. Still a picture of
                    their real product, so invented text inside it is a claim they
                    never made. Text fidelity is gated.
    GENERATED     — made from a brief. Its contents are invented by construction;
                    that is the point, and gating text would gate the mechanism.
    """

    USER_SUPPLIED = "user_supplied"
    RESTYLED = "restyled"
    GENERATED = "generated"


class Prominence(StrEnum):
    """How large an asset sits relative to its section.

    `imagery_treatment` says how to FRAME an image — chrome, bleed, shadow. It says
    nothing about size, so the builder chose, and chose small: four generated
    captures at quarter width, where the code and commit hashes that make them
    convincing are invisible. Unstated means defaulted.
    """

    DOMINANT = "dominant"
    SUPPORTING = "supporting"
    THUMBNAIL = "thumbnail"


class AssetKind(StrEnum):
    """What an asset IS, which decides what may be done to it.

    IMAGE — content imagery. May be generated from a brief, or restyled from an
            upload, because what it shows is a picture of a thing.
    VIDEO — a moving product asset. The sources for this category use video on
            3 of 3 pages and the harness could not represent one at all: the
            scout measured it, the design agent asked for it in prose, and then
            `Blueprint.assets` is defined as "one sentence per image" and the
            curator emits PNG. A video is user-supplied only — nothing here
            generates one — and it is never scrubbed or restyled, because both
            of those are raster passes over a single frame.
    LOGO  — the client's mark. It is a trademark, so it is RECOLOURED, NEVER
            REDRAWN: it never reaches `Curator.restyle` or `Curator.generate`.
            An image model asked to restyle a logo redraws the letterforms, and
            unlike a redrawn dashboard that is somebody's registered mark come
            back subtly wrong. It also never carries a `prominence` that means
            anything — see `step_build`, which keeps it out of the builder's
            asset list entirely so the "dominant asset owns the section" rule
            cannot fire on it. That rule firing on a nav asset is what produced
            the full-width blank box above the hero.
    """

    IMAGE = "image"
    VIDEO = "video"
    LOGO = "logo"


class Asset(BaseModel):
    id: str
    section_id: str
    kind: AssetKind = AssetKind.IMAGE
    brief: str                       # what it must show, from the blueprint
    prominence: Prominence = Prominence.SUPPORTING
    provenance: Provenance
    path: str                        # relative to the workspace's public/
    width: int = 0
    height: int = 0
    variants: dict[str, str] = Field(default_factory=dict)
    rejected: list[str] = Field(default_factory=list)
    # What the PII scrub replaced, by category and count. Never the original
    # value: this field is read by agents, written into prompts and copied into
    # logs, which are exactly the paths the scrub exists to keep the value off.
    scrubbed: list[str] = Field(default_factory=list)


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
    # Where the run got to. Held as a plain string rather than the Stage enum
    # because that lives in the orchestrator and importing it here is a cycle.
    #
    # It is here because it was nowhere: `Run.stage` lived only in memory, so
    # restarting the server sent every project back to `brief` and re-ran the
    # sources stage — three site extractions, real money, silently. The
    # orchestrator's own docstring claimed a run resumes from where it halted;
    # sections and decisions persisted, the pointer to the current stage did not.
    stage: str = "brief"
    brief: Brief | None = None
    constraints: list[Constraint] = Field(default_factory=list)
    design_system: DesignSystem | None = None
    sections: list[Section] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    decisions: list[Decision] = Field(default_factory=list)

    def active_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.superseded_by is None]

    def assets_for(self, section_id: str) -> list[Asset]:
        return [a for a in self.assets if a.section_id == section_id]

    def logo(self) -> Asset | None:
        """The client's mark, if they gave us one.

        Not `assets_for("nav")`: the logo is site-wide identity, not a nav
        image. It goes in the nav AND the footer, and it must never be handed to
        a builder as one of a section's images — that path carries prominence
        rules written for content imagery.
        """
        return next((a for a in self.assets if a.kind is AssetKind.LOGO), None)

    def next_pending(self) -> Section | None:
        pending = [s for s in self.sections if s.status is BuildStatus.PENDING]
        return min(pending, key=lambda s: s.order) if pending else None

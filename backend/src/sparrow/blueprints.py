"""Blueprint library loader.

Blueprints are markdown because a human maintains them and a human reviews
diffs to them. They describe structure and intent — never code, never
aesthetics. Aesthetics live in the design system; code is the builder's job.
"""

from __future__ import annotations

import re
from pathlib import Path

from sparrow.blackboard.schema import Blueprint

_FIELD = {
    "purpose": re.compile(r"^Purpose:\s*(.+?)(?=\n\n|\Z)", re.S | re.M),
    "slots": re.compile(r"^Slots:\s*(.+?)(?=\n\n|\Z)", re.S | re.M),
    "structure": re.compile(r"^Structure:\s*(.+?)(?=\n\n|\Z)", re.S | re.M),
}
_ID = re.compile(r"^#\s*Blueprint:\s*(\S+)", re.M)


def parse(text: str) -> Blueprint:
    def grab(key: str) -> str:
        m = _FIELD[key].search(text)
        if not m:
            raise ValueError(f"blueprint is missing a '{key.title()}:' field")
        return " ".join(m.group(1).split())

    m = _ID.search(text)
    if not m:
        raise ValueError("blueprint is missing its '# Blueprint: <id>' heading")

    slots = [s.strip(" `") for s in re.split(r"[·,]", grab("slots")) if s.strip(" `")]
    return Blueprint(
        id=m.group(1), purpose=grab("purpose"), slots=slots, structure=grab("structure")
    )


def load_dir(d: Path) -> dict[str, Blueprint]:
    out: dict[str, Blueprint] = {}
    for p in sorted(d.glob("*.md")):
        bp = parse(p.read_text())
        out[bp.id] = bp
    return out

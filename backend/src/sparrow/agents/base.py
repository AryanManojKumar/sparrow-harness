"""Shared agent machinery: prompt assembly and the model client.

Two rules live here rather than in any individual agent, because they must hold
for every one of them.

INJECTED, NEVER FETCHED. The brief, the constraints and the design system are
assembled into every prompt. There is deliberately no `get_brief` tool — a fetch
is skippable and an injection is not.

CONSTRAINTS ARE VERBATIM. They are the user's words, reproduced exactly. They
are never summarised, compressed, or reworded on the way into a prompt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from anthropic import Anthropic

from sparrow.blackboard.schema import Blackboard
from sparrow.render.tokens import FIDELITY, to_prompt

MODEL = "claude-opus-5"


def _tag(name: str, body: str) -> str:
    return f"<{name}>\n{body.strip()}\n</{name}>"


def context_block(bb: Blackboard) -> str:
    """The part of every agent prompt that is identical for every agent."""
    if bb.brief is None:
        raise ValueError("no brief on the blackboard — nothing may be generated yet")

    b = bb.brief
    brief = "\n".join([
        f"Category: {b.category}",
        f"Offering: {b.offering}",
        f"Audience: {b.audience}",
        f"Tone: {b.tone}",
        f"Primary action: {b.primary_action}",
        *([f"Secondary action: {b.secondary_action}"] if b.secondary_action else []),
    ])

    parts = [_tag("brief", brief)]

    active = bb.active_constraints()
    if active:
        parts.append(_tag(
            "hard_constraints",
            "These are the user's own words. They are absolute.\n"
            + "\n".join(f"- {c.text}" for c in active),
        ))

    if bb.design_system is not None:
        parts.append(_tag("design_system", to_prompt(bb.design_system)))

    return "\n\n".join(parts)


@dataclass
class Result:
    text: str
    input_tokens: int
    output_tokens: int


class Agent:
    """Base for every model-backed agent."""

    name: str = "agent"
    max_tokens: int = 8000

    def __init__(self, client: Anthropic | None = None) -> None:
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Put it in backend/.env "
                    "(see .env.example) or export it."
                )
            client = Anthropic()
        self.client = client

    def call(self, *, system: str, user: str) -> Result:
        msg = self.client.messages.create(
            model=MODEL,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        return Result(text, msg.usage.input_tokens, msg.usage.output_tokens)


FIDELITY_LINE = FIDELITY

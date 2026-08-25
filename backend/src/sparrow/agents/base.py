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

from sparrow.blackboard.schema import Blackboard
from sparrow.providers import Completion, Provider, Tier, get_provider
from sparrow.render.tokens import FIDELITY, to_prompt


def _tag(name: str, body: str) -> str:
    return f"<{name}>\n{body.strip()}\n</{name}>"


def stable_system(instructions: str, bb: Blackboard, extra: str = "") -> str:
    """Assemble everything that is IDENTICAL across every call an agent makes.

    Prompt caching is prefix-matched and has a floor — OpenAI will not cache a
    prefix under 1024 tokens, and Anthropic needs an explicit breakpoint. So the
    ordering rule is not stylistic:

        SYSTEM  = instructions + stack + brief + constraints + design system
        USER    = only what changes between calls (blueprint, section, images)

    Measured: with the context block left in the user message, the builder's
    identical prefix came to 995 tokens and cached nothing at all — 29 tokens
    under the floor. Moved here, it caches.
    """
    parts = [instructions.strip()]
    if extra.strip():
        parts.append(extra.strip())
    parts.append(context_block(bb))
    return "\n\n".join(parts)


def context_block(bb: Blackboard) -> str:
    """The part of every agent prompt that is identical for every agent."""
    if bb.brief is None:
        raise ValueError("no brief on the blackboard — nothing may be generated yet")

    b = bb.brief
    brief = "\n".join([
        *([f"PRODUCT NAME: {b.product_name} — use this exact name everywhere it "
           f"appears. Do not invent an alternative, do not abbreviate it, and do "
           f"not vary it between sections."] if b.product_name else
          ["PRODUCT NAME: not given — do NOT invent one. Refer to the product "
           "generically ('the platform') rather than naming it, so sections do "
           "not disagree."]),
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


class Agent:
    """Base for every model-backed agent.

    An agent declares the capability `tier` it needs and never names a model.
    Which model backs that tier is provider configuration — see
    `sparrow.providers`.
    """

    name: str = "agent"
    tier: Tier = Tier.MID
    max_tokens: int = 8000

    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or get_provider()
        # So a log line says "builder" rather than "openai".
        self.provider._agent_name = self.name

    def call(
        self, *, system: str, user: str, images: list[str] | None = None
    ) -> Completion:
        self.provider._agent_name = self.name
        return self.provider.complete(
            tier=self.tier, system=system, user=user,
            max_tokens=self.max_tokens, images=images,
        )


FIDELITY_LINE = FIDELITY

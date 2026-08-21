"""Provider abstraction.

Agents ask for a capability tier, never for a model name. Which model backs a
tier is configuration, so switching providers is an env var rather than a
refactor — and so a benchmark result can move one agent to a different tier
without touching its code.

Model ids verified against the live account, 2026-08-22.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Tier(StrEnum):
    """What an agent needs, not what it runs on.

    CHEAP — routing, classification, structured extraction. No judgement.
    MID   — interviewing, content, inspection. Judgement, bounded scope.
    TOP   — design direction, building, whole-page review. The output ceiling.
    """

    CHEAP = "cheap"
    MID = "mid"
    TOP = "top"


MODELS: dict[str, dict[Tier, str]] = {
    "anthropic": {
        Tier.CHEAP: "claude-haiku-4-5-20251001",
        Tier.MID: "claude-sonnet-5",
        Tier.TOP: "claude-opus-5",
    },
    "openai": {
        Tier.CHEAP: "gpt-5.6-luna",
        Tier.MID: "gpt-5.6-terra",
        Tier.TOP: "gpt-5.6-sol",
    },
}

# $ per million tokens (input, output), for the cost ledger. 2026-08-22.
PRICES: dict[str, dict[Tier, tuple[float, float]]] = {
    "anthropic": {Tier.CHEAP: (0.20, 1.20), Tier.MID: (3.00, 15.00), Tier.TOP: (5.00, 25.00)},
    "openai": {Tier.CHEAP: (0.20, 1.20), Tier.MID: (2.00, 12.00), Tier.TOP: (5.00, 30.00)},
}


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int

    def cost(self, provider: str, tier: Tier) -> float:
        pin, pout = PRICES[provider][tier]
        return self.input_tokens / 1e6 * pin + self.output_tokens / 1e6 * pout


class Provider(Protocol):
    name: str

    def complete(self, *, tier: Tier, system: str, user: str, max_tokens: int) -> Completion: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        from anthropic import Anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = Anthropic()

    def complete(self, *, tier: Tier, system: str, user: str, max_tokens: int) -> Completion:
        model = MODELS[self.name][tier]
        m = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in m.content if b.type == "text")
        return Completion(text, model, m.usage.input_tokens, m.usage.output_tokens)


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        from openai import OpenAI

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()

    def complete(self, *, tier: Tier, system: str, user: str, max_tokens: int) -> Completion:
        model = MODELS[self.name][tier]
        # The gpt-5.x line takes max_completion_tokens and rejects temperature.
        r = self.client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        u = r.usage
        return Completion(
            r.choices[0].message.content or "",
            model,
            u.prompt_tokens if u else 0,
            u.completion_tokens if u else 0,
        )


def get_provider(name: str | None = None) -> Provider:
    name = (name or os.environ.get("SPARROW_PROVIDER") or "openai").lower()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"unknown provider {name!r}; expected 'openai' or 'anthropic'")

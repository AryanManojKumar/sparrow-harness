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


# Cached input is discounted. OpenAI bills cache reads at 10% of input; Anthropic
# bills reads at 10% and writes at 125%. Both are worth designing prompts around:
# put everything stable first, everything variable last.
CACHE_READ_RATE = 0.10
CACHE_WRITE_RATE = {"openai": 1.00, "anthropic": 1.25}


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int          # uncached input only
    output_tokens: int
    cached_tokens: int = 0     # read from cache, billed at CACHE_READ_RATE
    cache_written: int = 0     # written to cache this call (Anthropic only)

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cached_tokens

    @property
    def cache_hit_rate(self) -> float:
        t = self.total_input
        return self.cached_tokens / t if t else 0.0

    def cost(self, provider: str, tier: Tier) -> float:
        pin, pout = PRICES[provider][tier]
        return (
            self.input_tokens / 1e6 * pin
            + self.cached_tokens / 1e6 * pin * CACHE_READ_RATE
            + self.cache_written / 1e6 * pin * CACHE_WRITE_RATE.get(provider, 1.0)
            + self.output_tokens / 1e6 * pout
        )

    def uncached_cost(self, provider: str, tier: Tier) -> float:
        """What this call would have cost with no caching — for the ledger."""
        pin, pout = PRICES[provider][tier]
        return self.total_input / 1e6 * pin + self.output_tokens / 1e6 * pout


class Provider(Protocol):
    name: str

    def complete(
        self, *, tier: Tier, system: str, user: str, max_tokens: int,
        images: list[str] | None = None, cache: bool = True,
    ) -> Completion: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        from anthropic import Anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = Anthropic()

    def complete(
        self, *, tier: Tier, system: str, user: str, max_tokens: int,
        images: list[str] | None = None, cache: bool = True,
    ) -> Completion:
        model = MODELS[self.name][tier]
        # Anthropic caches explicitly. The system block is identical across every
        # call an agent makes, so it is the natural breakpoint.
        sys_block: list[dict] = [{"type": "text", "text": system}]
        if cache:
            sys_block[0]["cache_control"] = {"type": "ephemeral"}

        content: list[dict] = []
        for b64 in images or []:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            })
        content.append({"type": "text", "text": user})

        m = self.client.messages.create(
            model=model, max_tokens=max_tokens, system=sys_block,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in m.content if b.type == "text")
        u = m.usage
        return Completion(
            text, model, u.input_tokens, u.output_tokens,
            cached_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_written=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        from openai import OpenAI

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()

    def complete(
        self, *, tier: Tier, system: str, user: str, max_tokens: int,
        images: list[str] | None = None, cache: bool = True,
    ) -> Completion:
        model = MODELS[self.name][tier]
        # OpenAI caches automatically on exact prefix match above ~1024 tokens —
        # there is nothing to opt into, but prompt ORDER decides whether it hits.
        content: list[dict] = [{"type": "text", "text": user}]
        for b64 in images or []:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        # The gpt-5.x line takes max_completion_tokens and rejects temperature.
        r = self.client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        )
        u = r.usage
        cached = 0
        if u and getattr(u, "prompt_tokens_details", None):
            cached = getattr(u.prompt_tokens_details, "cached_tokens", 0) or 0
        return Completion(
            r.choices[0].message.content or "",
            model,
            (u.prompt_tokens - cached) if u else 0,
            u.completion_tokens if u else 0,
            cached_tokens=cached,
        )


def get_provider(name: str | None = None) -> Provider:
    name = (name or os.environ.get("SPARROW_PROVIDER") or "openai").lower()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"unknown provider {name!r}; expected 'openai' or 'anthropic'")

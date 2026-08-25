"""The curator.

Produces the imagery the blueprints ask for, and guarantees what may be claimed
about each one.

Two paths, and the difference is not cosmetic:

GENERATED — made from a blueprint's asset brief, for a product that may not exist
yet or has nothing to screenshot. Its contents are invented by construction. That
is the point, so there is nothing to gate.

RESTYLED — the user's own screenshot, restyled to the design system. It is still a
picture of their real product, so any text the model adds is a claim they never
made. Measured in experiments/image-probe-02: asked to clean a capture whose copy
was truncated by a chat widget, the model completed the sentences — "frameworks,
adapt", "visibility across", "grow with you" — plausibly, well, and entirely
invented. The output looked flawless. That path is gated on text fidelity.

The gate is deliberately asymmetric. Gating generation would gate the mechanism;
not gating restyle ships fabricated claims about somebody's real product.
"""

from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from sparrow.agents.base import Agent
from sparrow.blackboard.schema import Asset, DesignSystem, Provenance
from sparrow.providers import Tier

IMAGE_MODEL = "gpt-image-2"

# Sizes gpt-image-2 accepts. Everything else is derived locally with Pillow.
_SIZES = {"wide": "1536x1024", "square": "1024x1024", "tall": "1024x1536"}


def _style_clause(ds: DesignSystem) -> str:
    """The design system, phrased for an image model rather than a builder."""
    pick = {c.token: c for c in ds.colors}
    parts = [
        f"ground: {pick['background'].value} ({pick['background'].name})",
        f"text: {pick['foreground'].value}",
        f"the only saturated colour is {pick['primary'].value} ({pick['primary'].name}), "
        "on primary actions and nothing else",
    ]
    if "accent" in pick:
        parts.append(f"{pick['accent'].name} {pick['accent'].value} at most once, "
                     "and only to mark something needing attention")
    parts += [
        f"headings in {ds.font_display}, body in {ds.font_body}",
        *([f"monospace ({ds.font_mono}) for any IDs, timestamps, paths or code"]
          if ds.font_mono else []),
        f"corners no rounder than {ds.radius_card}; hairline borders over filled cards",
        "no gradients, no glow, no coloured shadows",
    ]
    return "\n".join(f"- {p}" for p in parts)


TRANSCRIBE = """Transcribe every piece of text visible in this image, exactly as written.

One string per line, in reading order. Include labels, buttons, headings, body copy,
table cells, badges, timestamps and code. Do not correct spelling. Do not complete a
word or sentence that is cut off — transcribe only what you can actually read, and end
the line where the text becomes unreadable.

Output the lines and nothing else."""


@dataclass
class Fidelity:
    ok: bool
    invented: list[str]
    lost: list[str]

    def reason(self) -> str:
        if self.ok:
            return ""
        bits = []
        if self.invented:
            bits.append(f"{len(self.invented)} invented string(s): "
                        + "; ".join(repr(s) for s in self.invented[:4]))
        if self.lost:
            bits.append(f"{len(self.lost)} lost string(s)")
        return " · ".join(bits)


def _as_png(image: bytes) -> bytes:
    """Whatever the user uploaded, as the one format every path here expects.

    The upload is stored untouched — it is their file — so it may be a JPEG or a
    WebP. Normalising once, here, means the API contract, the fidelity
    comparison and the workspace all see the same bytes.
    """
    from PIL import Image

    if image[:8] == b"\x89PNG\r\n\x1a\n":
        return image
    buf = io.BytesIO()
    with Image.open(io.BytesIO(image)) as im:
        im.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def _words(lines: list[str]) -> set[str]:
    out: set[str] = set()
    for ln in lines:
        for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", ln):
            out.add(w.lower())
    return out


class Curator(Agent):
    name = "curator"
    tier = Tier.MID          # transcription and judgement, not design direction
    max_tokens = 4000

    # --------------------------------------------------------------- generate

    def generate(self, brief: str, ds: DesignSystem, *, shape: str = "wide") -> bytes:
        from openai import OpenAI

        prompt = (
            f"{brief}\n\n"
            "Render this as a realistic screenshot of real working software — not an "
            "illustration, not a mockup with placeholder boxes, not a diagram.\n\n"
            f"Match this design system:\n{_style_clause(ds)}\n\n"
            "Text must be legible and plausible. Any code, identifiers or timestamps must "
            "look like real values a working system would produce."
        )
        r = OpenAI().images.generate(
            model=IMAGE_MODEL, prompt=prompt, size=_SIZES[shape]
        )
        return base64.b64decode(r.data[0].b64_json)

    # ---------------------------------------------------------------- restyle

    def restyle(self, image: bytes, ds: DesignSystem, *, shape: str = "wide") -> bytes:
        from openai import OpenAI

        prompt = (
            "Restyle this screenshot to match a design system. This is a restyle, not a "
            "redesign.\n\n"
            f"{_style_clause(ds)}\n\n"
            "PRESERVE EXACTLY: the layout, the number of items, and every word of text. "
            "Do not invent copy. Do not complete a sentence that is cut off — if text is "
            "truncated at an edge, leave it truncated. Do not add controls that are not "
            "there. Changing what the interface says is a failure, however well it reads."
        )
        # Sent as a NAMED file, not a bare BytesIO. Without a name the SDK reports
        # the part as application/octet-stream and the API rejects the whole call
        # with "unsupported mimetype" — which is what this path did the first time
        # anything ever reached it. Nothing had, because until the asset gate
        # existed every image was generated and `restyle` was unreachable code.
        r = OpenAI().images.edit(
            model=IMAGE_MODEL,
            image=("image.png", io.BytesIO(_as_png(image)), "image/png"),
            prompt=prompt, size=_SIZES[shape],
        )
        return base64.b64decode(r.data[0].b64_json)

    # ----------------------------------------------------------------- gating

    def transcribe(self, image: bytes) -> list[str]:
        res = self.call(
            system=TRANSCRIBE, user="Transcribe this image.",
            images=[base64.b64encode(image).decode()],
        )
        return [ln.strip() for ln in res.text.splitlines() if ln.strip()]

    def check_fidelity(self, before: bytes, after: bytes) -> Fidelity:
        """Reject a restyle that says anything the original did not.

        Compared at word level rather than line level: a restyle legitimately
        reflows text, so line breaks move. A WORD that was not there before is
        the defect, and it is the one thing a visual diff will not catch.
        """
        src, dst = self.transcribe(before), self.transcribe(after)
        a, b = _words(src), _words(dst)
        invented = sorted(b - a)
        lost = sorted(a - b)
        return Fidelity(ok=not invented, invented=invented, lost=lost)


# ------------------------------------------------------------------- variants

VARIANTS: dict[str, tuple[int, int]] = {
    "hero": (1600, 900),
    "card": (800, 800),
    "mobile": (720, 900),
}


def derive_variants(path: Path) -> dict[str, str]:
    """Deterministic. No model, no cost — crop to centre and resize."""
    from PIL import Image

    out: dict[str, str] = {}
    with Image.open(path) as im:
        im = im.convert("RGB")
        for name, (w, h) in VARIANTS.items():
            target = w / h
            sw, sh = im.size
            if sw / sh > target:                     # too wide — crop sides
                nw = int(sh * target)
                box = ((sw - nw) // 2, 0, (sw + nw) // 2, sh)
            else:                                     # too tall — crop top/bottom
                nh = int(sw / target)
                box = (0, (sh - nh) // 2, sw, (sh + nh) // 2)
            v = path.with_name(f"{path.stem}--{name}.png")
            im.crop(box).resize((w, h), Image.LANCZOS).save(v)
            out[name] = v.name
    return out

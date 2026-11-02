"""How close a built page's colour comes to a reference's brand.

CLAUDE.md §5: learning layout from a reference is fine; reproducing its
distinctive look is not. The free-design builder needs a check on that, because
it is the one thing a model designing from screenshots does without meaning to:
experiment B took VALORANT's red and THE FINALS' red and landed ΔE ≈ 10 from
both — the same colour to most eyes.

Measured on what the page shows, not what the code says: a Tailwind class, a
CSS variable and a hex literal all paint the same pixel, and only the pixel is
what a visitor compares. Neutrals say nothing about whose brand a page is, so
only saturated colours are compared. Distance is CIE76 ΔE in Lab: under ~10
reads as the same colour, 10–25 as a close relative, above 40 as unrelated.
"""

from __future__ import annotations

import colorsys
import io

# Closer than this to a reference's brand colour is a finding. Between "the same
# colour" (10) and "a close relative" (25), nearer the first: a related hue is a
# category convention, an identical one is somebody's brand.
TOO_CLOSE = 15.0
# A colour on less of the page than this is a detail, not a palette.
MIN_SHARE = 0.003


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def lab(rgb) -> tuple[float, float, float]:
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(x)) for x in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a, b) -> float:
    la, lb = lab(a), lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def saturated(rgb) -> bool:
    _, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return s > 0.35 and 0.15 < l < 0.85


def page_accents(images: list[bytes], k: int = 4) -> list[tuple[str, float]]:
    """The page's most prominent saturated colours, with their share of pixels."""
    from PIL import Image

    counts: dict[tuple[int, int, int], int] = {}
    total = 0
    for data in images:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im = im.resize((max(1, im.width // 4), max(1, im.height // 4)))
        pixels = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
        for rgb in pixels:
            total += 1
            if saturated(rgb):
                q = tuple((c // 24) * 24 + 12 for c in rgb)
                counts[q] = counts.get(q, 0) + 1  # type: ignore[index]
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:k]
    return [("#%02x%02x%02x" % c, n / total) for c, n in top if total and n / total >= MIN_SHARE]


def reference_colours(palette: dict) -> list[str]:
    """A reference's saturated colours as the scout recorded them.

    `brand` reads every paint — text, borders, SVG — and is what catches a red
    that lives on buttons; `surfaces` and `accent` are the older, area-only
    readings, kept so projects scouted before `brand` existed still check.
    """
    cols = list(palette.get("brand") or [])
    cols += [s["hex"] for s in palette.get("surfaces", [])] + [palette.get("accent") or ""]
    out: list[str] = []
    for c in cols:
        if c and c not in out and saturated(hex_rgb(c)):
            out.append(c)
    return out


def too_close(images: list[bytes], palettes: dict[str, dict]) -> list[dict]:
    """Every page accent within TOO_CLOSE of some reference's brand colour."""
    hits: list[dict] = []
    for colour, share in page_accents(images):
        for site, pal in palettes.items():
            for ref in reference_colours(pal):
                de = delta_e(hex_rgb(colour), hex_rgb(ref))
                if de < TOO_CLOSE:
                    hits.append({"page": colour, "share": round(share, 4), "site": site,
                                 "reference": ref, "delta_e": round(de, 1)})
    return sorted(hits, key=lambda h: h["delta_e"])

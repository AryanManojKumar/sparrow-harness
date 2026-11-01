"""How close does each built page's colour come to a reference's brand?

Takes the most prominent saturated colours off each variant's full-page screenshot
(the neutrals — black, white, greys — say nothing about whose brand it is) and finds
the nearest saturated colour in each reference's palette as the scout recorded it
(`sources/palettes.json`). Distance is CIE76 ΔE in Lab: under ~10 reads as the same
colour to most people, 10–25 as a close relative, above 40 as unrelated.

    uv run python ../experiments/dsh-builder-02/brand.py b c cplus bplus
"""

from __future__ import annotations

import colorsys
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PALETTES = json.loads((ROOT / "projects/fps-shooter/sources/palettes.json").read_text())


def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lab(rgb) -> tuple[float, float, float]:
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(x)) for x in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def _de(a, b) -> float:
    la, lb = _lab(a), _lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def _saturated(rgb) -> bool:
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return s > 0.35 and 0.15 < l < 0.85


def page_accents(kind: str, k: int = 4) -> list[tuple[str, float]]:
    shots = sorted((HERE / "out" / "shots").glob(f"{kind}-home-*.jpg"))
    counts: dict[tuple[int, int, int], int] = {}
    total = 0
    for p in shots:
        im = Image.open(p).convert("RGB")
        im = im.resize((im.width // 4, im.height // 4))
        for rgb in im.getdata():
            total += 1
            if _saturated(rgb):
                q = tuple((c // 24) * 24 + 12 for c in rgb)
                counts[q] = counts.get(q, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:k]
    return [("#%02x%02x%02x" % c, n / total) for c, n in top]


def ref_colours(site: str) -> list[str]:
    p = PALETTES[site]
    cols = [s["hex"] for s in p.get("surfaces", [])] + [p.get("accent", "")]
    return [c for c in cols if c and _saturated(_hex(c))]


if __name__ == "__main__":
    for kind in sys.argv[1:]:
        acc = page_accents(kind)
        print(f"\n{kind}: page accents " + ", ".join(f"{h} ({s:.1%})" for h, s in acc))
        for site in PALETTES:
            refs = ref_colours(site)
            if not refs or not acc:
                print(f"   vs {site:24s} (no saturated reference colours recorded)")
                continue
            best = min(((_de(_hex(a), _hex(r)), a, r) for a, _ in acc for r in refs))
            print(f"   vs {site:24s} closest ΔE {best[0]:5.1f}  ({best[1]} ~ {best[2]})")

"""Painting substituted values over located PII. Deterministic, no model, no cost.

A dashboard screenshot is only worth uploading because it looks like real
software in real use. That rules out the obvious scrub: blurring every name and
figure returns a grey smear, and a user who gets one back stops uploading. So
this module SUBSTITUTES — same character shape, same width, same ink colour,
same position — and blurs only where there is nothing to substitute (a face).

Two things had to be solved to make substitution work at the pixel level.

BOXES FROM A VISION MODEL ARE SHORT. Measured against a real payments dashboard
carrying 25 findings: every box the model returned was left-accurate and
right-short by roughly one character — "Sarah Ree|d", "acmemarket|s.com",
"£12,843.2|1". Filling exactly those boxes would leave the last digit of a
balance and the last letter of a surname standing. So the model's box is treated
as a POINTER, not a boundary: `_snap` pads it, finds the actual ink, and grows
the fill to the real extent of the drawn characters.

THE FONT IS NOT KNOWN. It is measured rather than assumed: each candidate face
is rendered at every plausible size and scored on how closely it reproduces the
ORIGINAL string's measured ink box. The face and size that reproduce it best are
the ones used to draw the replacement. That is why a monospace transaction id
comes back monospace without anyone declaring it.
"""

from __future__ import annotations

import hashlib
import io
import random
import re
from dataclasses import dataclass
from pathlib import Path

# Faces to measure against. Liberation is metric-compatible with the Arial /
# Helvetica the vast majority of product UIs actually render in; DejaVu is the
# fallback that ships nearly everywhere. If neither is present — a slim base
# image with no fonts at all — substitution is impossible and the caller blurs
# instead, which is worse-looking but never a leak.
_FACES: dict[str, tuple[str, ...]] = {
    "sans": (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ),
    "mono": (
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    ),
}


def available_faces() -> dict[str, str]:
    out = {}
    for kind, paths in _FACES.items():
        for p in paths:
            if Path(p).exists():
                out[kind] = p
                break
    return out


# --------------------------------------------------------------- what to say

# `money` and `phone` are never taken from the model. Their whole meaning is
# shape — a currency symbol, a thousands separator, a digit count — and the
# model returned "£000,000.00" and "pay_XXXXXXXX" when asked, which is the grey
# smear again in text form. Shape is reproduced mechanically instead.
_MECHANICAL = {"money", "phone"}

KINDS = {"person_name", "email", "phone", "postal_address",
         "org_name", "identifier", "money", "face"}

# Stripe-style ids carry a type tag before the underscore — `pay_`, `pout_`,
# `cus_`. The tag says what the row is, not who it belongs to, so it survives.
# The lookahead is not decoration: without it `acme_markets` reads as a tagged
# id and the scrub preserves the customer's name as the "tag". A tag is only a
# tag when what follows it is opaque — digits somewhere in the body.
_TYPE_TAG = re.compile(r"^([a-z]{2,6}[_-])(?=[A-Za-z0-9]*\d)")
# A trailing TLD. Reshaping it turns an email into gibberish for no privacy gain.
_TLD = re.compile(r"(\.[A-Za-z]{2,4})$")
_RUN = re.compile(r"[A-Za-z0-9]+")


def _rng(seed: str) -> random.Random:
    """Seeded from the original string, so the same value always becomes the
    same replacement — within one image, across its variants, and across a
    replay of the whole run."""
    return random.Random(hashlib.sha256(seed.encode()).hexdigest())


def reshape(text: str, *, seed: str | None = None) -> str:
    """Same characters, different values. Letters stay letters and keep their
    case, digits stay digits, everything else is untouched — so the string keeps
    its width, its separators and its register."""
    r = _rng(seed or text)
    head = m.group(1) if (m := _TYPE_TAG.match(text)) else ""
    tail = m.group(1) if (m := _TLD.search(text)) else ""
    body = text[len(head):len(text) - len(tail)]

    out, seen_digit = [], False
    for ch in body:
        if ch.isdigit():
            # Only the FIRST digit of the string is held away from zero — a
            # replacement reading "£0,000.00" is a placeholder, but "£1,045.00"
            # needs the zero after the separator to stay possible.
            out.append(ch if ch == "0" and seen_digit is False
                       else r.choice("0123456789" if seen_digit else "123456789"))
            seen_digit = True
        elif ch.isalpha():
            src = "abcdefghijklmnopqrstuvwxyz"
            out.append(r.choice(src.upper() if ch.isupper() else src))
        else:
            out.append(ch)
    return head + "".join(out) + tail


def _is_mask(s: str) -> bool:
    """`XXXXXXXX`, `000,000.00`, `••••` — a redaction that admits it is one."""
    alnum = [c.lower() for c in s if c.isalnum()]
    if not alnum:
        return True
    return max(alnum.count(c) for c in set(alnum)) / len(alnum) > 0.6


def _usable(original: str, suggested: str) -> bool:
    """A suggestion is usable if it changed the identifying head of the string
    and did not turn into a mask. The head is checked rather than the whole
    string because "Acme Markets" -> "Apex Markets" is correct: `Markets` is a
    category word, `Acme` is the customer."""
    if not suggested or suggested.lower() == original.lower() or _is_mask(suggested):
        return False
    if not 0.6 <= len(suggested) / max(len(original), 1) <= 1.6:
        return False
    first = _RUN.search(original)
    return bool(first) and first.group(0).lower() not in suggested.lower()


def _words(pair: tuple[str, str]) -> dict[str, str]:
    """Word-level map from one original/replacement pair.

    This is what keeps the image coherent. `Acme Markets` appears three more
    times in the payments capture — as `acme_markets`, inside
    `sarah.reed@acmemarkets.com`, and nowhere the model reliably connects them.
    Mapping `acme -> apex` and applying it to every other string replaces the
    customer everywhere at once, instead of leaving a sidebar reading
    "Apex Markets" above a footer reading "sarah.reed@acmemarkets.com".
    """
    a, b = _RUN.findall(pair[0]), _RUN.findall(pair[1])
    if len(a) != len(b):
        return {pair[0].lower(): pair[1]} if len(pair[0]) >= 4 else {}
    return {x.lower(): y for x, y in zip(a, b)
            if len(x) >= 4 and x.lower() != y.lower()}


def _recase(sample: str, word: str) -> str:
    """Wear the case of the occurrence being replaced. `Acme Markets` seeds
    `acme -> Apex`; dropped into an email unchanged that produced
    `Maya.Stone@Apexmarkets.com`, which no mail client would have written."""
    if sample.isupper() and len(sample) > 1:
        return word.upper()
    if sample.islower():
        return word.lower()
    if sample[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


def _apply_words(text: str, words: dict[str, str]) -> str:
    """Longest source first, so `acmemarkets` is not half-rewritten by `acme`
    landing before a longer key had its turn."""
    out = text
    for src in sorted(words, key=len, reverse=True):
        out = re.sub(re.escape(src),
                     lambda m: _recase(m.group(0), words[src]),
                     out, flags=re.IGNORECASE)
    return out


def _residue(original: str, candidate: str) -> str:
    """Reshape any word of the original that survived into the candidate.

    The word map only knows the entities that were located as names. If the
    customer appears ONLY inside an email domain and never as a display name,
    `sarah.reed@acmemarkets.com` maps to `alex.smith@acmemarkets.com` and the
    customer ships. Whatever run of four or more characters came through
    unchanged is reshaped here, and nothing else is touched.
    """
    out = candidate
    for run in sorted(set(_RUN.findall(original)), key=len, reverse=True):
        if len(run) >= 4 and run.lower() in out.lower():
            out = re.sub(re.escape(run), reshape(run), out, flags=re.IGNORECASE)
    return out


def resolve(items: list[tuple[str, str, str]]) -> dict[str, str]:
    """original -> replacement, for every located string.

    `items` is (text, kind, suggestion). Names and organisations resolve first
    because they seed the word map that keeps everything else consistent.
    """
    names = [i for i in items if i[1] in ("person_name", "org_name", "postal_address")]
    rest = [i for i in items if i not in names]

    out: dict[str, str] = {}
    words: dict[str, str] = {}
    for text, _kind, sug in names:
        if text in out:
            continue
        out[text] = sug if _usable(text, sug) else reshape(text)
        words.update(_words((text, out[text])))

    for text, kind, sug in rest:
        if text in out:
            continue
        if kind in _MECHANICAL:
            out[text] = reshape(text)
            continue
        mapped = _apply_words(text, words)
        if mapped != text:
            out[text] = _residue(text, mapped)
        elif _usable(text, sug):
            out[text] = _residue(text, _apply_words(sug, words))
        else:
            out[text] = reshape(text)
    return out




# ------------------------------------------------------------ where to say it


@dataclass
class Box:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def w(self) -> int:
        return self.x1 - self.x0

    @property
    def h(self) -> int:
        return self.y1 - self.y0


def to_pixels(box: list[float] | tuple[float, ...], size: tuple[int, int]) -> Box:
    """The model reports in a 0-1000 space on each axis independently."""
    w, h = size
    x0, y0, x1, y1 = (float(v) for v in box)
    return Box(max(0, min(w, int(x0 / 1000 * w))), max(0, min(h, int(y0 / 1000 * h))),
               max(0, min(w, int(x1 / 1000 * w))), max(0, min(h, int(y1 / 1000 * h))))


def _modal(px) -> tuple[int, int, int]:
    counts: dict[tuple[int, int, int], int] = {}
    for p in px:
        counts[p] = counts.get(p, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def _runs(flags: list[bool], bridge: int = 0) -> list[tuple[int, int]]:
    """Contiguous True spans, bridging gaps of at most `bridge`."""
    out: list[tuple[int, int]] = []
    for i, on in enumerate(flags):
        if not on:
            continue
        if out and i - out[-1][1] <= bridge + 1:
            out[-1] = (out[-1][0], i)
        else:
            out.append((i, i))
    return out


_BUCKETS = 24


def _buckets(cols: list[int]) -> list[float]:
    """A column profile at a fixed resolution, scaled to its own maximum — so
    two strings compare on where their ink sits, not on how wide or dark they
    are."""
    if not cols:
        return [0.0] * _BUCKETS
    top = max(cols) or 1
    out = []
    for i in range(_BUCKETS):
        a = i * len(cols) // _BUCKETS
        b = max(a + 1, (i + 1) * len(cols) // _BUCKETS)
        out.append(sum(cols[a:b]) / (b - a) / top)
    return out


class _Ruler:
    """Font measurement, memoised.

    Placement scores dozens of candidate extents per finding, so the size that
    renders `text` at a given ink height is worked out once per (face, height)
    and reused.
    """

    def __init__(self, faces: dict[str, str]) -> None:
        self.faces = faces
        self._cache: dict[tuple[str, str, int], tuple[int, int, int]] = {}
        self._profiles: dict[tuple[str, str, int], list[float]] = {}

    def at(self, path: str, text: str, height: int) -> tuple[int, int, int]:
        """(size, width, height) of `text` rendered as close to `height` as the
        face allows."""
        from PIL import ImageFont

        key = (path, text, height)
        if key in self._cache:
            return self._cache[key]
        best = (8, 0, 0)
        err = None
        for size in range(6, max(8, height * 3 + 6)):
            l, t, r, b = ImageFont.truetype(path, size).getbbox(text)
            w, h = r - l, b - t
            if w <= 0 or h <= 0:
                continue
            e = abs(h - height)
            if err is None or e < err:
                err, best = e, (size, w, h)
        self._cache[key] = best
        return best

    def profile(self, path: str, text: str, height: int) -> list[float]:
        """Where the ink falls across `text`, as `_BUCKETS` normalised columns.

        Width alone cannot tell one string from another. `Apple Pay •••• 1010`
        and `Foo Food Suppliers Ltd` render to within 3px of the same width at
        the same line height, and the model had put the second one's box on the
        first one's row — so a width-only match repainted the wrong row of the
        table and left the beneficiary's name standing. The shape of the ink
        separates them.
        """
        from PIL import ImageFont

        key = (path, text, height)
        if key not in self._profiles:
            size, _w, _h = self.at(path, text, height)
            mask = ImageFont.truetype(path, size).getmask(text, mode="L")
            mw, mh = mask.size
            cols = [sum(mask.getpixel((x, y)) for y in range(mh)) for x in range(mw)]
            self._profiles[key] = _buckets(cols)
        return self._profiles[key]

    def score(self, text: str, cols: list[int], h: int) -> tuple[float, str, int]:
        """How badly each face misses the ink actually drawn in a span when it
        draws `text`. Lower is better; the winning face is the one to draw with.

        Two terms: how far off the WIDTH is, and how far off the SHAPE is.
        """
        w = len(cols)
        seen = _buckets(cols)
        out = None
        for path in self.faces.values():
            size, rw, _rh = self.at(path, text, h)
            want = self.profile(path, text, h)
            e = (abs(rw - w) / max(w, 1)
                 + 2.0 * sum(abs(a - b) for a, b in zip(seen, want)) / _BUCKETS)
            if out is None or e < out[0]:
                out = (e, path, size)
        return out or (9.9, "", 8)


# A placement scoring worse than this is not the string the model named.
# Measured over the 25 findings on the payments capture: the 23 that landed on
# the right characters scored 0.19 to 0.47, an avatar monogram matched against
# its chip scored 2.44, and a card's last four digits matched against a word one
# table row away scored 0.78. Everything above the line is caught by the
# verification pass in `Curator.scrub` instead.
_TOLERANCE = 0.60

# Above this share of ink, the region is a filled block rather than characters —
# the avatar chip behind a monogram. Fitting a font to a solid square found a
# 40pt match and painted two enormous letters across the account name beside it.
_SOLID = 0.55

# The model's box was short by up to two characters and never long by more than
# a quarter, so a span far wider than the box is not the string it named. Without
# this, the two letters of an avatar monogram matched a span that ran from the
# chip across the account name beside it, and were repainted at 40pt.
_SPAN_WIDTH = (0.55, 2.0)


def _place(im, box: Box, text: str, ruler: _Ruler, *,
           threshold: int = 40, band: float = 1.2, anchored: bool = True):
    """Find the ink that actually spells `text` near the model's box.

    The model's box is a POINTER. Measured on the payments capture it was short
    by one to two characters on the right in most cases, swallowed a leading
    `MID:` label in one, and sat a whole row high in two others. So the box says
    roughly where to look; WHICH ink gets repainted is decided by measuring: of
    every run of characters near that point, the one whose width matches what
    `text` should be at that line's height wins.

    Three constraints keep the measurement honest, and each one is a defect that
    happened without it:

    - the span must cover the box's horizontal CENTRE. Without it, `5555` matched
      the four `••••` bullets to its left just as well, and was painted there.
    - `anchored` requires the line to overlap the box vertically. Without it,
      `£42,210.34` matched the words `to pay out` on the label line above, at a
      font size small enough to make any width fit.
    - the span must not be a solid block, nor far wider than the box itself —
      see `_SOLID` and `_SPAN_WIDTH`.

    Returns (tight box, background, ink, face path, font size) or None.
    """
    W, H = im.size
    pad_x = max(10, round(box.h * 2.0))
    pad_y = max(4, round(box.h * band))
    rx0, ry0 = max(0, box.x0 - pad_x), max(0, box.y0 - pad_y)
    rx1, ry1 = min(W, box.x1 + pad_x), min(H, box.y1 + pad_y)
    if rx1 - rx0 < 2 or ry1 - ry0 < 2:
        return None

    region = im.crop((rx0, ry0, rx1, ry1))
    rw, rh = region.size
    px = list(region.get_flattened_data())
    bg = _modal(px)
    ink_at = [_dist(p, bg) > threshold for p in px]
    if not any(ink_at):
        return None

    lines = _runs([any(ink_at[y * rw:(y + 1) * rw]) for y in range(rh)])
    bx0, bx1 = box.x0 - rx0, box.x1 - rx0
    bcx = (bx0 + bx1) // 2

    best = None
    for top, bot in lines:
        lh = bot - top + 1
        if lh < 3 or not 0.5 <= lh / max(box.h, 1) <= 2.0:
            continue
        if anchored and (bot + ry0 < box.y0 or top + ry0 > box.y1):
            continue
        counts = [sum(1 for y in range(top, bot + 1) if ink_at[y * rw + x])
                  for x in range(rw)]
        cum = [0]
        for c in counts:
            cum.append(cum[-1] + c)
        # Bridge only what antialiasing and letter spacing open up, so the word
        # runs stay separable and a span can stop short of a `MID:` label. At
        # 0.22 of the line height a card's `•••• 5555` fused into one run twice
        # the width of the box, and the last four digits could not be isolated.
        words = _runs([c > 0 for c in counts], bridge=max(1, round(lh * 0.15)))
        centre = next((i for i, (a, b) in enumerate(words) if a <= bcx <= b), None)
        if centre is None:
            continue
        # Gaps BETWEEN consecutive runs, not from one end of the span to the
        # other: measured end-to-end, `To Green Valley Farms` looked like a
        # 41px gap because the two words in the middle were counted as one, and
        # the correct span was never enumerated at all.
        gaps = [words[k + 1][0] - words[k][1] for k in range(len(words) - 1)]
        for i in range(centre + 1):
            for j in range(centre, len(words)):
                if any(g > lh * 1.6 for g in gaps[i:j]):     # ran into the next column
                    break
                x0, x1 = words[i][0], words[j][1]
                w = x1 - x0 + 1
                if not _SPAN_WIDTH[0] <= w / max(box.w, 1) <= _SPAN_WIDTH[1]:
                    continue
                if (cum[x1 + 1] - cum[x0]) / (w * lh) > _SOLID:
                    continue
                err, path, size = ruler.score(text, counts[x0:x1 + 1], lh)
                if best is None or err < best[0]:
                    best = (err, top, bot, x0, x1, path, size)

    if best is None or best[0] > _TOLERANCE:
        return None
    _err, top, bot, x0, x1, path, size = best

    # The ink colour is the modal of the DARKEST quarter of the ink, not of all
    # of it: most ink pixels in antialiased UI text are partial coverage, so
    # taking the plain mode drew every substitution in pale grey.
    dark = sorted((_dist(p, bg), p) for p, on in zip(px, ink_at) if on)
    core = [p for _d, p in dark[max(0, int(len(dark) * 0.75)):]]
    ink = _modal(core) if core else (0, 0, 0)

    return (Box(rx0 + x0, ry0 + top, rx0 + x1 + 1, ry0 + bot + 1), bg, ink, path, size)


def _pixelate(crop):
    """Mosaic, not blur. A Gaussian wide enough to hide a 34px avatar averages
    the crop to one flat grey rectangle, which is the grey smear this module
    exists to avoid — visible damage on an image that had nothing real in it.
    A mosaic keeps the colour and reads as a deliberate privacy treatment.
    """
    from PIL import Image

    w, h = crop.size
    block = max(2, min(w, h) // 5)
    return (crop.resize((max(1, w // block), max(1, h // block)), Image.BOX)
                .resize((w, h), Image.NEAREST))


def paint(image: bytes, found: list[dict]) -> tuple[bytes, list[dict]]:
    """Substitute every located string; mask what cannot be substituted.

    `found` items carry `text`, `kind`, `box` (0-1000) and `replacement`.
    Anything outside a located box is left byte-identical: this repaints the
    rectangles it measured and nothing else, so a screenshot with no PII in it
    comes back unchanged rather than merely similar.

    Every placement is measured against a PRISTINE copy before anything is
    drawn. Measuring as it went made the result order-dependent: the avatar chip
    was repainted first, and the account name next to it was then measured
    against the paint that had just landed on top of it.

    A finding whose text cannot be placed is MASKED at the model's own box
    rather than skipped. Skipping would mean the value stays in the image
    exactly when placement is least certain, which is the one outcome the scrub
    exists to prevent.

    Returns the image and the findings that were acted on.
    """
    from PIL import Image, ImageDraw, ImageFont

    im = Image.open(io.BytesIO(image)).convert("RGB")
    faces = available_faces()
    ruler = _Ruler(faces)

    plan: list[tuple[dict, Box, object]] = []
    for f in found:
        box = to_pixels(f["box"], im.size)
        if box.w <= 1 or box.h <= 1:
            continue
        # Nothing substitutes for a photograph of a person, and nothing draws
        # text on a machine with no fonts installed. Blur is the honest fallback.
        if f["kind"] == "face" or not faces or not f.get("replacement"):
            plan.append((f, box, None))
            continue
        placed = _place(im, box, f["text"], ruler)
        if placed is None:
            # The model's vertical placement is off by a whole table row often
            # enough to be worth a second look before giving up and blurring:
            # two rows of the payments capture's activity table were reported
            # against the row above, ~50px away on a 12px line. The band widens
            # past a neighbouring row and the anchor drops, but the width
            # measurement and the span-width bound still have to agree.
            placed = _place(im, box, f["text"], ruler, band=4.5, anchored=False)
        plan.append((f, box, placed))

    draw = ImageDraw.Draw(im)
    done: list[dict] = []
    for f, box, placed in plan:
        if placed is None:
            pad = max(2, round(min(box.w, box.h) * 0.2))
            r = (max(0, box.x0 - pad), max(0, box.y0 - pad),
                 min(im.size[0], box.x1 + pad), min(im.size[1], box.y1 + pad))
            if r[2] <= r[0] or r[3] <= r[1]:
                continue
            im.paste(_pixelate(im.crop(r)), r)
            done.append(dict(f, blurred=True))
            continue

        tight, bg, ink, path, size = placed
        font = ImageFont.truetype(path, size)
        l, t, r, b = font.getbbox(f["replacement"])
        if r - l > tight.w * 1.15 and size > 6:            # replacement ran long
            size = max(6, int(size * tight.w * 1.15 / (r - l)))
            font = ImageFont.truetype(path, size)
            l, t, r, b = font.getbbox(f["replacement"])

        draw.rectangle((tight.x0 - 1, tight.y0 - 1, tight.x1, tight.y1), fill=bg)
        draw.text((tight.x0 - l, tight.y0 - t), f["replacement"], font=font, fill=ink)
        done.append(f)

    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), done

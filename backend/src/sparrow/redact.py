"""Painting substituted values over located PII. Deterministic, no model, no cost.

A dashboard screenshot is only worth uploading because it looks like real
software in real use. That rules out the obvious scrub: blurring every name and
figure returns a grey smear, and a user who gets one back stops uploading. So
this module SUBSTITUTES — same character shape, same width, same ink colour,
same position — and masks only where there is nothing to substitute (a face, or
a value that could not be placed).

Three things had to be solved to make substitution work at the pixel level, and
each of them is a defect that happened first.

BOXES FROM A VISION MODEL ARE SHORT. Measured against a real payments dashboard
carrying 25 findings, every box was left-accurate and right-short by one to two
characters — "Sarah Ree|d", "acmemarket|s.com", "£12,843.2|1". One swallowed a
leading `MID:` label; two sat a whole table row out. Filling exactly those boxes
leaves the last digit of a balance standing. So the box is a POINTER, not a
boundary: `_place` searches around it and measures which ink to repaint.

WIDTH ALONE IS NOT ENOUGH TO IDENTIFY A STRING. `Apple Pay •••• 1010` and
`Foo Food Suppliers Ltd` render within 3px of the same width at the same line
height. The ink PROFILE (`_buckets`) separates them.

BUT MATCHING CANNOT DECIDE WHICH ROW. Measured over five locate responses for
one capture, 5.1% of placements landed on a row other than the one the model
pointed at — a beneficiary's name painted across the `View all activity ›` link
at the foot of the table, a card's last four digits painted 48px down into the
row below. The match error does not separate those from the good placements:
in-row errors ran 0.115-0.599 and crossing errors 0.450-0.579, one distribution
on top of the other. No tolerance tells them apart. So the row is a HARD
GEOMETRIC BOUND (`_ROW_SLACK`), nothing overrides it, and a value that is not on
the row the model pointed at gets masked there rather than relocated. Same
capture, same measurement, after: 0 of 112.

THE FONT IS NOT KNOWN. It is measured rather than assumed: each candidate face
is rendered at every plausible size and scored on how closely it reproduces the
ORIGINAL string's ink. The face and size that reproduce it best draw the
replacement — which is why a monospace transaction id comes back monospace
without anyone declaring it.
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
# ISO currency codes read as three ordinary letters to a shape-preserving
# reshape, which turned `USD 98,450.00` into `TOB 11,025.76`. A currency code
# says what the number is denominated in, not whose money it is.
_CURRENCY = re.compile(r"\b(?:[A-Z]{3})\b")
_CODES = {"USD", "EUR", "GBP", "CNY", "JPY", "CHF", "AUD", "CAD", "INR", "SGD",
          "HKD", "NZD", "SEK", "NOK", "DKK", "ZAR", "AED", "BRL", "MXN", "PLN"}


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
    keep = {m.span() for m in _CURRENCY.finditer(text) if m.group(0) in _CODES}
    head = m.group(1) if (m := _TYPE_TAG.match(text)) else ""
    tail = m.group(1) if (m := _TLD.search(text)) else ""
    body = text[len(head):len(text) - len(tail)]

    off = len(head)
    out, seen_digit = [], False
    for i, ch in enumerate(body):
        if any(a <= i + off < b for a, b in keep):
            out.append(ch)
            continue
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


# Reshaping a NAME letter by letter gives `Vfhm oc Wzrxq, Enckbkip Ydvsdp` —
# which is not a business, does not read as one, and is the grey smear again.
# Where the model's own suggestion is unusable, a name is drawn from here
# instead, seeded from the original so it stays stable across a replay.
_GIVEN = ("Alex", "Jordan", "Maya", "Priya", "Sam", "Nina", "Omar", "Lena",
          "Theo", "Rosa", "Kai", "Ines", "Noah", "Zara", "Felix", "Anya")
_FAMILY = ("Hart", "Okafor", "Nakamura", "Bennett", "Duarte", "Kowalski",
           "Ferreira", "Lindqvist", "Osei", "Marchetti", "Halvorsen", "Baptiste")
_FIRM = ("Northwind", "Bluecrest", "Fairmark", "Ridgeline", "Kestrel", "Silverlane",
         "Oakford", "Meridian", "Harborview", "Ardent", "Copperline", "Larkmoor")
_SUFFIX = ("Trading", "Holdings", "Partners", "Industrial", "Logistics", "Group",
           "Supplies", "Systems", "Ventures", "Foods", "Imports", "Exports")


def _invent(text: str, kind: str) -> str:
    """A plausible name of roughly the right length, seeded from the original."""
    r = _rng(text)
    pool = (_GIVEN, _FAMILY) if kind == "person_name" else (_FIRM, _SUFFIX)
    parts = [r.choice(p) for p in pool]
    # Keep any trailing legal form — `Ltd.`, `Inc.`, `LLC`, `Co.` — because it
    # says what kind of entity it is, not which one.
    tail = [w for w in re.split(r"\s+", text) if w.rstrip(".").upper() in
            {"LTD", "INC", "LLC", "PLC", "CO", "GMBH", "SA", "AG", "BV", "NV"}]
    return " ".join(parts + tail[-1:])


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
    for text, kind, sug in names:
        if text in out:
            continue
        out[text] = sug if _usable(text, sug) else _invent(text, kind)
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

# How far a line's centre may sit outside the model's box and still count as the
# row the box points at. The model's vertical placement is good to a few pixels
# and its box is often a little short, so a quarter of the box height absorbs
# the honest error without reaching the next row — table rows in the captures
# measured here are 51px apart on a 12px line.
_ROW_SLACK = 0.25


def _place(im, box: Box, text: str, ruler: _Ruler, *, threshold: int = 40):
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
    - the line must BE the row the box points at, not merely touch it — see
      `_ROW_SLACK`. This is a HARD bound and nothing overrides it.
    - the span must not be a solid block, nor far wider than the box itself —
      see `_SOLID` and `_SPAN_WIDTH`.

    Returns (tight box, background, ink, face path, font size) or None.
    """
    W, H = im.size
    pad_x = max(10, round(box.h * 2.0))
    pad_y = max(4, round(box.h * 1.2))
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
        # THE ROW BOUND. Overlapping the box was not enough: the search region
        # reaches past a neighbouring row, so a line one row down can still
        # clip the box and win on width. Measured over five locate responses
        # for the same capture, 7.6% of placements landed on another row that
        # way — a beneficiary name painted across `View all activity ›`, a
        # card's last four digits painted 48px down into the row below.
        #
        # Matching cannot fix this: over those same runs the in-row match
        # errors ran 0.115-0.599 and the crossing errors 0.347-0.587. The two
        # distributions sit on top of each other, so no tolerance separates
        # them. Geometry does, and only geometry.
        lcy = (top + bot) / 2 + ry0
        slack = max(2.0, box.h * _ROW_SLACK)
        if not box.y0 - slack <= lcy <= box.y1 + slack:
            continue
        if abs(lcy - (box.y0 + box.y1) / 2) > max(box.h, lh) * 0.6:
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

    return (Box(rx0 + x0, ry0 + top, rx0 + x1 + 1, ry0 + bot + 1), bg, ink, path, size, _err)


def _cover(im, box: Box, threshold: int = 40) -> Box:
    """Grow a box sideways to the full extent of the ink it lands on.

    Masking at the model's raw box was too literal: its boxes are short and
    sometimes a few pixels left, so a mask over `•••• 4242` covered the bullets
    and the first digit and left `242` sitting in the open — three quarters of
    a card number, and scrappy-looking with it. This walks out along the box's
    OWN ROW to the ends of the ink runs the box touches.

    Vertically it does not move at all. The row bound is the whole guarantee.
    """
    W, H = im.size
    pad = max(6, box.h)
    reach = max(8.0, box.w * 1.25)      # how far out it may grow, each side
    rx0, rx1 = max(0, round(box.x0 - reach)), min(W, round(box.x1 + reach))
    # Sampled a little taller than the box so a clipped glyph top or bottom
    # still registers as ink. The MASK still uses the box's own rows: this
    # widens what is looked at, never what is painted.
    vpad = max(1, round(box.h * 0.35))
    ry0, ry1 = max(0, box.y0 - vpad), min(H, box.y1 + vpad)
    if rx1 - rx0 < 2 or ry1 - ry0 < 2:
        return box

    region = im.crop((rx0, ry0, rx1, ry1))
    rw, rh = region.size
    px = list(region.get_flattened_data())
    bg = _modal(px)
    cols = [any(_dist(px[y * rw + x], bg) > threshold for y in range(rh))
            for x in range(rw)]
    # Bridged at the gap tolerance `_place` itself spans across, so a word the
    # span stopped short of still counts as part of the same value: the span for
    # `Greenfield Imports Ltd.` covered `Greenfield Imports` and a 0.5-height
    # bridge could not reach `Ltd.`, which then survived beside the replacement.
    runs = _runs(cols, bridge=max(2, round(box.h * 1.2)))
    lo, hi = box.x0 - rx0, box.x1 - rx0
    touched = [(a, b) for a, b in runs if b >= lo and a <= hi]
    if not touched:
        return box
    x0, x1 = min(a for a, _b in touched), max(b for _a, b in touched)
    # Clipped to `reach` rather than abandoned when the run is long. On a
    # tightly set cell the label, the bullets and the digits bridge into one
    # run, and giving up there is what leaves `242` in the open; growing
    # without a bound would mask the whole cell including its label.
    x0 = max(x0, lo - reach)
    x1 = min(x1, hi + reach)
    return Box(rx0 + round(x0), box.y0, rx0 + round(x1) + 1, box.y1)


def _pixelate(crop):
    """Mosaic, not blur. A Gaussian wide enough to hide a 34px avatar averages
    the crop to one flat grey rectangle, which is the grey smear this module
    exists to avoid — visible damage on an image that had nothing real in it.
    A mosaic keeps the colour and reads as a deliberate privacy treatment.
    """
    from PIL import Image

    w, h = crop.size
    # The block has to be a fair fraction of the LINE HEIGHT or it destroys
    # nothing: at a fifth of a 12px row the mosaic was 2px and `Greenfield
    # Imports Ltd.` was still legible straight through it.
    block = max(3, round(min(w, h) * 0.6))
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
    pristine = im.copy()
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
        # No unanchored rescue. There was one — it widened the band past the
        # neighbouring rows and dropped the vertical anchor, to catch boxes the
        # model had put a whole row out. It caught those, and it is also how a
        # beneficiary's name came to be painted over the table's `View all
        # activity ›` link. Where the value is not on the row the model pointed
        # at, this masks instead: a mosaic on the right row beats a name on the
        # wrong one, and painting over somebody's UI control is not a trade
        # worth making for a tidier substitution.
        plan.append((f, box, _place(im, box, f["text"], ruler)))

    draw = ImageDraw.Draw(im)
    done: list[dict] = []
    for f, box, placed in plan:
        if placed is None:
            box = _cover(im, box)
            pad = max(2, round(min(box.w, box.h) * 0.2))
            # Vertical padding is capped so a mask cannot bleed into the row
            # above or below either. The row bound is the whole guarantee: what
            # this module changes stays on the row the model pointed at,
            # whether it substitutes there or masks there.
            pad_y = min(pad, max(1, box.h // 4))
            r = (max(0, box.x0 - pad), max(0, box.y0 - pad_y),
                 min(im.size[0], box.x1 + pad), min(im.size[1], box.y1 + pad_y))
            if r[2] <= r[0] or r[3] <= r[1]:
                continue
            im.paste(_pixelate(im.crop(r)), r)
            done.append(dict(f, blurred=True))
            continue

        tight, bg, ink, path, size, err = placed
        font = ImageFont.truetype(path, size)
        l, t, r, b = font.getbbox(f["replacement"])
        if r - l > tight.w * 1.15 and size > 6:            # replacement ran long
            size = max(6, int(size * tight.w * 1.15 / (r - l)))
            font = ImageFont.truetype(path, size)
            l, t, r, b = font.getbbox(f["replacement"])

        # Clear the whole word the span sits in, not just the span. The model's
        # text and what is rendered differ at the ends — `Greenfield Imports
        # Ltd.` matched a span that stopped before `Ltd.`, and the tail survived
        # beside the replacement as `Silverwood Trading LLCLtd.`; an email one
        # character shorter left a stray `n`. Same row, bounded reach.
        fill = _cover(pristine, tight)
        draw.rectangle((fill.x0 - 1, tight.y0 - 1, fill.x1, tight.y1), fill=bg)
        draw.text((tight.x0 - l, tight.y0 - t), f["replacement"], font=font, fill=ink)
        # `at` is what was actually repainted, against `box` which is where the
        # model said to look. A caller comparing the two can see a placement
        # that crossed to another row; `test_scrub` and the spread harness do.
        done.append(dict(f, at=[tight.x0, tight.y0, tight.x1, tight.y1], err=round(err, 3)))

    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), done

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

Upstream of both sits the SCRUB. An uploaded dashboard is full of real customer
data — the capture the asset gate was built against carries `Sarah Reed`,
`sarah.reed@acmemarkets.com`, a merchant id and eleven sterling amounts, and the
text-fidelity gate faithfully preserved every one of them into the published
page. `scrub` runs first, before `restyle`, because `restyle` posts the file to a
third-party image model and a published asset ends up on the open web: after
either, the data has already left. See `sparrow.redact` for the pixel work.
"""

from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from sparrow import redact
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


SCRUB = """You locate personal and customer-identifying data in a screenshot of software.

Report every instance of these, and nothing else:

- person_name     a named individual
- email           an email address
- phone           a telephone number
- postal_address  a street address
- org_name        the name of a CUSTOMER, CLIENT, MERCHANT, BENEFICIARY, VENDOR or
                  COUNTERPARTY — a third party whose business appears in this account
- identifier      an id that picks out a PERSON, an ACCOUNT or a COUNTERPARTY — a
                  merchant, customer, invoice or transaction id, the last four digits
                  of a card, a monogram or initials taken from a person's name. NOT an
                  id that picks out a piece of work: a run, job, build, deployment,
                  request, trace, commit or ticket id belongs to the software, not to
                  anybody, and changing it changes what the screenshot says the
                  product does.
- money           an amount carrying a currency symbol or code
- face            a photograph of a person

Report NOTHING else. In particular, leave alone: the wordmark, logo or product name of
the software itself; navigation labels, menu items, tab names and breadcrumbs; column
headers, metric labels, field labels, button text, tooltips and status words; dates and
times; counts and percentages with no currency symbol; source code, file paths, API
routes, error strings, branch names, repository names and version numbers. Those are what makes the image legible as
working software, and an image that loses them is worth nothing to anybody.

For every instance report:

  "text"        the string exactly as written, character for character
  "kind"        one of the labels above
  "box"         [x0, y0, x1, y1] in a 0-1000 coordinate space over the whole image —
                x on the width, y on the height, tight around the drawn characters
  "replacement" a value the same system could have produced instead

Rules for "replacement":

- The same length as "text", the same capitalisation pattern, the same punctuation, the
  same currency symbol, the same number of digits, the same separators.
- Never a masking string. Not XXXX, not 0000, not ####, not asterisks or bullets. It must
  read as a real value, because the point of the image is that it shows real software.
- It must not contain the identifying part of the original.
- The same real-world entity often appears several times in one image — as a display
  name, as an id, inside an email domain, as initials on an avatar. Replace every one of
  them from the SAME invented entity, so the image still hangs together after the swap.
- For "face", report an empty string.

Output one JSON object: {"found": [...]}. Nothing else. If there is nothing to report,
output {"found": []}."""

_JSON = re.compile(r"\{.*\}", re.S)


@dataclass
class Scrub:
    """A scrubbed image and what changed in it.

    `changed` records the CATEGORY, the REPLACEMENT and the count — never the
    original value. The blackboard is read by agents and written into prompts and
    logs, so a record that carried `sarah.reed@acmemarkets.com` would put the leak
    back on exactly the paths the scrub exists to keep it off. What the user
    needs in order to check the work is the scrubbed image itself, which is
    written next to their upload.
    """

    image: bytes
    changed: list[str]
    lines: list[str]          # the scrubbed image transcribed, for `check_fidelity`

    @property
    def clean(self) -> bool:
        return not self.changed


# Shapes that are PII wherever they appear and cannot be confused with product
# chrome: a currency amount and an email address. Deliberately not ids or bare
# numbers — a version string, a row count and a port number all look like those,
# and a sweep that fires on them masks the parts of the screenshot worth keeping.
_SHAPES = (
    re.compile(r"[£$€¥]\s?\d[\d,]*\.\d{2}"),
    re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}"),
)


def _still_reads(text: str, lines: list[str]) -> bool:
    """Whether `text` is still in the image, allowing for the two reads of the
    same row disagreeing.

    Exact substring was not enough. Measured live: a beneficiary the locate pass
    transcribed as `Foo Food Suppliers Ltd` came back from the read-back as
    `To Food Suppliers Ltd`, the substring test found nothing, and the row
    shipped unscrubbed while the report said it had been replaced. Two shared
    long words on one line is the same rule `_same_value` already uses to pair
    the passes up.
    """
    if len(text) >= 4 and any(text in line for line in lines):
        return True
    words = {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", text)}
    if len(words) < 2:
        return False
    return any(len(words & {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", line)}) >= 2
               for line in lines)


def _unlocated(lines: list[str], plan: list[dict]) -> list[dict]:
    """PII shapes in the read-back that the locate pass never named.

    The verify step only re-checked the values the model had already found, so a
    value it never found was never checked. Measured across five live runs of
    the same capture, the locate pass missed two of the activity table's payout
    amounts on one run and found them on the others — recall varies run to run
    just as placement does. Whatever the sweep turns up is masked, never
    substituted: there is no box for it and no transcription to trust.
    """
    # The REPLACEMENTS have to count as known too. They are money-shaped by
    # construction — that is the whole point of substituting rather than
    # masking — so a sweep that only knows the originals reports every amount
    # it just substituted as an unlocated leak, and masks the lot on the retry.
    known = " ".join(f"{f['text']} {f.get('replacement', '')}" for f in plan)
    out: list[dict] = []
    for line in lines:
        for shape in _SHAPES:
            for hit in shape.findall(line):
                if hit not in known and not any(d["text"] == hit for d in out):
                    out.append({"text": hit, "kind": "money" if hit[0] not in
                                "abcdefghijklmnopqrstuvwxyz" else "email"})
    return out


def _same_value(text: str, among: list[dict]) -> dict | None:
    """Whether a second-pass finding is one of the values that survived the
    first. Compared on shared words rather than exact string, because the two
    reads of the same row differ: the beneficiary the model first transcribed as
    `Foo Food Suppliers Ltd` came back as `To Food Suppliers Ltd`."""
    words = {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", text)}
    for f in among:
        if f["text"] == text:
            return f
        if len(words & {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", f["text"])}) >= 2:
            return f
    return None


class Curator(Agent):
    name = "curator"
    tier = Tier.MID          # transcription and judgement, not design direction
    max_tokens = 8000       # a dense dashboard scrubs to ~30 findings

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

    # ---------------------------------------------------------------- scrubbing

    def _locate(self, image: bytes) -> list[dict]:
        """One vision pass: every reportable value, with a box and a suggestion."""
        res = self.call(
            system=SCRUB, user="Locate everything reportable in this image.",
            images=[base64.b64encode(image).decode()],
        )
        m = _JSON.search(res.text)
        if not m:
            return []
        try:
            found = json.loads(m.group(0)).get("found", [])
        except json.JSONDecodeError:
            return []
        return [dict(f, text=str(f.get("text", "")).strip(),
                     replacement=str(f.get("replacement", "")).strip())
                for f in found
                if isinstance(f, dict) and isinstance(f.get("box"), list)
                and len(f["box"]) == 4 and f.get("kind") in redact.KINDS
                and (str(f.get("text", "")).strip() or f.get("kind") == "face")]

    def scrub(self, image: bytes) -> Scrub:
        """Substitute the real people, customers and amounts out of an upload.

        MUST run before `restyle`. `restyle` posts the file to a third-party
        image model and what comes back is published to the preview URL; after
        either, the customer data is already out and scrubbing only cleans the
        copy nobody was worried about.

        The scrub itself reads the real bytes — it has to, it is a vision call —
        so this does not make the upload never leave the machine. What it buys is
        that exactly ONE call sees the real values and nothing downstream does:
        not the image model, not the fidelity transcription, not the derived
        variants, not the published page.

        A clean image comes back byte-identical, not merely similar: `paint`
        repaints the rectangles it measured and touches nothing else, so an empty
        finding is a no-op by construction.
        """
        png = _as_png(image)
        found = self._locate(png)
        if not found:
            return Scrub(png, [], self.transcribe(png))

        # Replacements are resolved HERE, not taken as the model gave them. The
        # first probe against the payments capture came back with "£000,000.00"
        # and "pay_XXXXXXXXXXXX" — masks, which is the grey smear this whole
        # approach exists to avoid — and with "alex.smith@acmemarkets.com",
        # which renamed the person and kept the customer.
        chosen = redact.resolve([(f["text"], f["kind"], f["replacement"])
                                 for f in found if f["kind"] != "face"])
        plan = [dict(f, replacement=chosen.get(f["text"], "")) for f in found]
        out, done = redact.paint(png, plan)

        # VERIFY, then one retry. The scrub is unattended, and the way it fails
        # is not noisy: the model puts a box on the row above, the width happens
        # to match the row it landed on, and a beneficiary's name is still in the
        # image while the report says it was replaced. Reading the result back is
        # the only check that catches that, and it costs nothing — the fidelity
        # gate downstream needs this transcription anyway.
        lines = self.transcribe(out)

        # LOOK AGAIN AT THE IMAGE, unconditionally — do not ask the
        # transcription whether a second look is needed. Measured: a
        # beneficiary sat on the second line of a two-line cell, the model's box
        # named the first line, the mask landed on `Payout` and left
        # `To Food Suppliers Ltd` legible underneath — and the read-back did not
        # report it, so a transcription-gated retry never ran. The read-back is
        # a vision call too; a value it cannot see is not a value that is gone.
        # One more locate costs about three cents and does not depend on it.
        # What the read-back says is still legible, by name and by shape.
        survived = [f for f in plan if _still_reads(f["text"], lines)]
        # Plus anything PII-shaped the locate pass never named at all. Checking
        # only what the model found means a miss is invisible to the check.
        survived += _unlocated(lines, plan)

        second = [f for f in self._locate(out)
                  if _same_value(f["text"], plan + survived) is not None]
        if second or survived:
            # The retry MASKS rather than substituting again. Substitution
            # already failed for these values once — measured on the payments
            # capture, `Sarah Reed` survived a second substitution pass too,
            # because the second pass places against the same approximate box
            # and makes the same mistake. A mosaic over the box the model just
            # named cannot miss, and one masked name beats a published one.
            retry = [dict(f, replacement="") for f in second]
            if retry:
                out, more = redact.paint(out, retry)
                done += more
                lines = self.transcribe(out)

        left = {f["text"] for f in plan if _still_reads(f["text"], lines)}
        left |= {f["text"] for f in _unlocated(lines, plan)}
        if len(left) > max(1, len(plan) // 5):
            # DEGRADE, do not ship a half-substituted image. Measured on a dense
            # trade-finance capture — 36 findings, several near-identical account
            # numbers stacked in one narrow column: placements crossed rows, one
            # IBAN was drawn over an organisation's name while the original IBAN
            # stayed put, and the result was both damaged AND leaky. Masking
            # every located value is uglier and tells the user the truth: this
            # capture is too dense to substitute, send a simpler one.
            out, done = redact.paint(png, [dict(f, replacement="") for f in plan])
            lines = self.transcribe(out)
            return Scrub(out, [f"{len(plan)} value(s) masked — too many to place "
                               "individually on a capture this dense"], lines)

        tally: dict[str, int] = {}
        for f in done:
            tally[f["kind"]] = tally.get(f["kind"], 0) + 1
        changed = [f"{k.replace('_', ' ')} ×{n}" for k, n in sorted(tally.items())]
        masked = sum(1 for f in done if f.get("blurred"))
        if masked:
            changed.append(f"{masked} masked rather than substituted")
        if left:
            changed.append(f"{len(left)} value(s) still readable after two passes")
        return Scrub(out, changed, lines)

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

    def check_fidelity(self, before: bytes | list[str], after: bytes) -> Fidelity:
        """Reject a restyle that says anything the original did not.

        Compared at word level rather than line level: a restyle legitimately
        reflows text, so line breaks move. A WORD that was not there before is
        the defect, and it is the one thing a visual diff will not catch.

        `before` is the image the restyle was GIVEN, which since the scrub is
        the scrubbed image, not the user's upload — see `step_assets`. It may be
        passed as already-transcribed lines, because the scrub read the scrubbed
        image back to verify itself and there is no reason to buy that twice.
        """
        src = before if isinstance(before, list) else self.transcribe(before)
        dst = self.transcribe(after)
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

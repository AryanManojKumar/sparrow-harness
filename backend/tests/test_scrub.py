"""The PII scrub: what it replaces, and what it must leave alone.

CLAUDE.md §7 calls this cheap early and painful to retrofit. The reason it is
worth a test file of its own is that it has two failure directions and they pull
against each other:

- it misses a customer's name, and a real person's data is published; or
- it flattens the screenshot, and the upload is worth nothing. A dashboard is
  only worth uploading because it looks like real software in real use, so a
  scrub that blurs every figure and label returns a grey smear — and the user
  responds by not uploading anything, which is the differentiator gone.

Everything here is deterministic: the vision call that LOCATES values is stubbed,
and what is under test is the substitution and the pixel work, which take no
model and cost nothing. The live exercise against the real payments capture is
recorded in `experiments/scrub-01`.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from sparrow import redact

FACES = redact.available_faces()
needs_fonts = pytest.mark.skipif(
    not FACES, reason="no system font to draw a substitution with")


# --------------------------------------------------------------- what it says


def test_a_figure_keeps_its_shape_and_loses_its_value():
    """Not `£000,000.00`. A masked amount is the grey smear in text form: the
    screenshot stops looking like a working system, which is the only reason it
    was uploaded."""
    out = redact.reshape("£125,430.28")
    assert out != "£125,430.28"
    assert len(out) == len("£125,430.28")
    assert out[0] == "£" and out[4] == "," and out[8] == "."
    assert out[1] != "0", "a leading zero reads as a placeholder"
    assert all(c.isdigit() for c in out if c not in "£,.")


def test_the_same_value_always_becomes_the_same_replacement():
    """`£42,210.34` appears twice in the payments capture, in two different
    cards. Seeded from the string itself, both become the same figure — which is
    also what makes a run replayable."""
    assert redact.reshape("£42,210.34") == redact.reshape("£42,210.34")
    assert redact.reshape("£42,210.34") != redact.reshape("£42,210.35")


def test_an_id_keeps_its_type_tag_and_loses_its_body():
    out = redact.reshape("pay_01JTVX8Z8Q3K6Y6Z7J9X2V1F4P")
    assert out.startswith("pay_"), "the tag says what the row is, not whose it is"
    assert out != "pay_01JTVX8Z8Q3K6Y6Z7J9X2V1F4P"
    assert len(out) == len("pay_01JTVX8Z8Q3K6Y6Z7J9X2V1F4P")


def test_a_customer_name_is_not_mistaken_for_a_type_tag():
    """`acme_markets` looks exactly like `pay_...` to a prefix rule, and a scrub
    that "preserves the tag" would preserve the customer. A tag is only a tag
    when what follows it is opaque."""
    assert "acme" not in redact.reshape("acme_markets")


def test_an_email_keeps_its_tld():
    out = redact.reshape("sarah.reed@acmemarkets.com")
    assert out.endswith(".com") and "@" in out
    assert "sarah" not in out and "acmemarkets" not in out


def test_money_never_takes_the_model_s_suggestion():
    """Asked for a replacement, the model returned `£000,000.00` and
    `pay_XXXXXXXXXXXX` — masks. Shape is the whole meaning of a figure, so it is
    reproduced mechanically instead."""
    out = redact.resolve([("£125,430.28", "money", "£000,000.00")])
    assert out["£125,430.28"] != "£000,000.00"
    assert set(out["£125,430.28"]) - set("£,.0") , "not a mask"


def test_a_masked_suggestion_is_refused_for_a_name_too():
    out = redact.resolve([("Sarah Reed", "person_name", "XXXXX XXXX")])
    assert out["Sarah Reed"] != "XXXXX XXXX"
    assert "Sarah" not in out["Sarah Reed"]


def test_a_suggestion_that_keeps_the_customer_is_refused():
    """The model's first answer for the footer was `alex.smith@acmemarkets.com`:
    it renamed the person and kept the customer."""
    out = redact.resolve([
        ("Sarah Reed", "person_name", "Alex Smith"),
        ("sarah.reed@acmemarkets.com", "email", "alex.smith@acmemarkets.com"),
    ])
    assert "acmemarkets" not in out["sarah.reed@acmemarkets.com"]


def test_one_entity_is_replaced_consistently_everywhere_it_appears():
    """`Acme Markets` appears three more times in the payments capture — as a
    merchant id, inside an email domain, and as a display name. Replaced
    independently, the sidebar reads `Apex Markets` above a footer reading
    `sarah.reed@acmemarkets.com`, which is both a leak and incoherent."""
    out = redact.resolve([
        ("Acme Markets", "org_name", "Apex Markets"),
        ("acme_markets", "identifier", "apex_markets"),
        ("sarah.reed@acmemarkets.com", "email", "alex.smith@acmemarkets.com"),
    ])
    stem = out["Acme Markets"].split()[0].lower()
    assert stem in out["acme_markets"].lower()
    assert stem in out["sarah.reed@acmemarkets.com"].lower()
    assert not any("acme" in v.lower() for v in out.values())


def test_a_category_word_is_allowed_to_survive():
    """`Markets` is what kind of business it is; `Acme` is which one. Requiring
    every word to change turns `Acme Markets` into noise for no privacy gain."""
    out = redact.resolve([("Acme Markets", "org_name", "Apex Markets")])
    assert out["Acme Markets"] == "Apex Markets"


def test_a_replacement_wears_the_case_of_what_it_replaces():
    out = redact.resolve([
        ("Acme Markets", "org_name", "Apex Markets"),
        ("acme_markets", "identifier", ""),
    ])
    assert out["acme_markets"].islower(), \
        "an id is lowercase; `Apex_markets` is not a value any system produced"


# ------------------------------------------------------------- where it says it


def shot(rows: list[tuple[int, int, str, int]], size=(560, 200)) -> Image.Image:
    """A flat screenshot: dark text on white, which is what a dashboard is."""
    im = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(im)
    for x, y, text, px in rows:
        d.text((x, y), text, font=ImageFont.truetype(next(iter(FACES.values())), px),
               fill=(24, 24, 27))
    return im


def as_png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def box_of(im: Image.Image, x0, y0, x1, y1) -> list[float]:
    w, h = im.size
    return [x0 / w * 1000, y0 / h * 1000, x1 / w * 1000, y1 / h * 1000]


def differing(a: bytes, b: bytes) -> set[tuple[int, int]]:
    ia, ib = Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB")
    return {(x, y) for y in range(ia.size[1]) for x in range(ia.size[0])
            if ia.getpixel((x, y)) != ib.getpixel((x, y))}


def test_an_image_with_nothing_to_report_comes_back_byte_identical():
    """Not "similar" — identical. A scrub that re-encodes every clean upload is
    a scrub that quietly degrades every clean upload."""
    png = as_png(shot([(10, 10, "Gross volume", 16)])) if FACES else b""
    if not FACES:
        pytest.skip("no fonts")
    out, done = redact.paint(png, [])
    assert out == png and done == []


@needs_fonts
def test_a_substitution_touches_only_the_line_it_was_pointed_at():
    """The measured guarantee. `paint` repaints the rectangles it measured and
    nothing else, so `Gross volume` two lines up cannot be collateral."""
    im = shot([(10, 10, "Gross volume", 15),
               (10, 40, "Sarah Reed", 15),
               (10, 70, "Successful", 15)])
    before = as_png(im)
    after, done = redact.paint(before, [{
        "text": "Sarah Reed", "kind": "person_name",
        "box": box_of(im, 10, 40, 82, 55), "replacement": "Maya Stone",
    }])

    assert len(done) == 1 and not done[0].get("blurred")
    ys = {y for _x, y in differing(before, after)}
    assert ys, "something must have changed"
    assert min(ys) > 25 and max(ys) < 68, \
        f"the neighbouring lines were disturbed: rows {min(ys)}-{max(ys)}"


@needs_fonts
def test_a_short_box_still_covers_the_whole_value():
    """Measured on the payments capture: the model's boxes were left-accurate
    and right-short by one to two characters — `Sarah Ree|d`, `£12,843.2|1`.
    Filling exactly those boxes leaves the last digit of a balance standing."""
    im = shot([(10, 40, "£125,430.28", 15)])
    before = as_png(im)
    short = box_of(im, 10, 40, 70, 55)          # stops two characters early
    after, _done = redact.paint(before, [{
        "text": "£125,430.28", "kind": "money",
        "box": short, "replacement": "£663,734.26",
    }])
    xs = {x for x, _y in differing(before, after)}
    with Image.open(io.BytesIO(before)) as b:
        ink = [x for x in range(b.size[0])
               if any(b.getpixel((x, y)) != (255, 255, 255) for y in range(35, 62))]
    assert max(xs) >= max(ink), \
        "the tail of the figure survived the fill the model's box asked for"


@needs_fonts
def test_a_box_on_the_wrong_line_is_blurred_rather_than_repainted_wrong():
    """The model put two of the payments capture's boxes a whole table row out.
    Where nothing near the box measures like the string it named, the value is
    blurred: skipping it would leave it readable exactly when placement is least
    certain."""
    im = shot([(10, 40, "Gross volume", 15)])
    before = as_png(im)
    after, done = redact.paint(before, [{
        "text": "Sarah Reed Junior The Third", "kind": "person_name",
        "box": box_of(im, 10, 40, 300, 55), "replacement": "Maya Stone Senior The First",
    }])
    assert done and done[0].get("blurred") is True
    assert after != before


@needs_fonts
def test_a_face_is_blurred_because_there_is_nothing_to_substitute():
    im = shot([(10, 40, "Gross volume", 15)])
    before = as_png(im)
    after, done = redact.paint(before, [{
        "text": "", "kind": "face", "box": box_of(im, 8, 35, 100, 60),
        "replacement": "",
    }])
    assert done and after != before


@needs_fonts
def test_the_replacement_is_drawn_in_the_ink_the_line_was_written_in():
    """Taking the plain mode of the ink drew every substitution in the pale grey
    of the antialiased edges, so a scrubbed dashboard read as a faded one."""
    im = shot([(10, 40, "Sarah Reed", 15)])
    after, _ = redact.paint(as_png(im), [{
        "text": "Sarah Reed", "kind": "person_name",
        "box": box_of(im, 10, 40, 82, 55), "replacement": "Maya Stone",
    }])
    with Image.open(io.BytesIO(after)) as a:
        darkest = min(sum(a.getpixel((x, y))) for y in range(35, 62)
                      for x in range(8, 90))
    assert darkest < 200, "the substituted text is paler than the text it replaced"


# ---------------------------------------------------- verifying and degrading


class FakeCurator:
    """`Curator.scrub` with the two model calls replaced by scripted answers.

    `locates` is one list of findings per `_locate` call; `reads` is one
    transcription per `transcribe` call. What is under test is the control flow
    between them — verify, retry, and the decision to stop substituting.
    """

    def __init__(self, locates, reads):
        from sparrow.agents.curator import Curator

        self.locates, self.reads = list(locates), list(reads)
        self.located = self.read = 0
        self.scrub = Curator.scrub.__get__(self)
        self.transcribe = lambda _img: self._read()
        self._locate = lambda _img: self._next_locate()

    def _read(self):
        self.read += 1
        return self.reads[min(self.read - 1, len(self.reads) - 1)]

    def _next_locate(self):
        self.located += 1
        return self.locates[min(self.located - 1, len(self.locates) - 1)]


def finding(text, kind="person_name", box=(10, 200, 150, 275), replacement="Maya Stone"):
    return {"text": text, "kind": kind, "box": list(box), "replacement": replacement}


@needs_fonts
def test_a_clean_image_costs_one_read_and_comes_back_untouched():
    im = shot([(10, 40, "Gross volume", 15)])
    cur = FakeCurator(locates=[[]], reads=[["Gross volume"]])
    out = cur.scrub(as_png(im))

    assert out.clean and out.image == as_png(im)
    assert out.lines == ["Gross volume"], \
        "the fidelity gate needs this transcription, so the scrub hands it on"
    assert cur.located == 1 and cur.read == 1


@needs_fonts
def test_a_value_that_survived_the_first_pass_is_looked_for_again():
    """The failure is quiet: the model boxes the row above, the width happens to
    match what it landed on, and the beneficiary is still in the image while the
    report says it was replaced. Reading the result back is the only check that
    catches it."""
    im = shot([(10, 40, "Sarah Reed", 15)])
    cur = FakeCurator(
        locates=[[finding("Sarah Reed", box=(500, 500, 540, 540))],   # nowhere near
                 [finding("Sarah Reed", box=box_of(im, 10, 40, 82, 55))]],
        reads=[["Sarah Reed"], ["Maya Stone"], ["Maya Stone"]])
    out = cur.scrub(as_png(im))

    assert cur.located == 2, "a survivor must be looked for a second time"
    assert "Sarah Reed" not in "\n".join(out.lines)


@needs_fonts
def test_the_retry_reuses_the_first_pass_replacement():
    """Otherwise the second pass invents a different name for the same person,
    and an image where one row says Maya Stone and another says someone else is
    not a picture of anybody's product."""
    im = shot([(10, 40, "Sarah Reed", 15)])
    cur = FakeCurator(
        locates=[[finding("Sarah Reed", box=(500, 500, 540, 540))],
                 [finding("Sarah Reed", box=box_of(im, 10, 40, 82, 55),
                          replacement="Someone Else")]],
        reads=[["Sarah Reed"], ["?"], ["?"]])
    cur.scrub(as_png(im))
    # The second locate's own suggestion is discarded; nothing in the image is
    # allowed to disagree with what pass one decided.
    assert cur.located == 2


@needs_fonts
def test_too_many_survivors_stops_substituting_and_masks_everything():
    """Measured on a dense trade-finance capture: 36 findings, several
    near-identical account numbers stacked in one narrow column. Placements
    crossed rows — an IBAN was drawn over an organisation's name while the
    original IBAN stayed put — and the result was both damaged AND leaky.
    Masking is uglier and tells the user the truth: send a simpler capture."""
    im = shot([(10, 40, "Sarah Reed", 15), (10, 70, "Jane Doe Two", 15),
               (10, 100, "John Roe Three", 15)])
    nowhere = (900, 900, 940, 940)
    cur = FakeCurator(
        locates=[[finding("Sarah Reed", box=nowhere),
                  finding("Jane Doe Two", box=nowhere),
                  finding("John Roe Three", box=nowhere)]],
        # every read still shows them: nothing the scrub tried actually landed
        reads=[["Sarah Reed", "Jane Doe Two", "John Roe Three"]])
    out = cur.scrub(as_png(im))

    assert not out.clean
    assert "masked" in out.changed[0] and "too many to place" in out.changed[0]
    assert cur.located == 2, "one retry, then it stops — §8 caps loops"

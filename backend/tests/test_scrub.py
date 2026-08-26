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
    assert out.image != as_png(im)


@needs_fonts
def test_the_retry_masks_rather_than_substituting_again():
    """Measured on the payments capture: `Sarah Reed` survived a SECOND
    substitution pass too, because the second pass places against the same
    approximate box and makes the same mistake. A mosaic over the box the model
    just named cannot miss, and one masked name beats a published one."""
    im = shot([(10, 40, "Sarah Reed", 15)])
    cur = FakeCurator(
        locates=[[finding("Sarah Reed", box=(500, 500, 540, 540))],
                 [finding("Sarah Reed", box=box_of(im, 10, 40, 82, 55))]],
        reads=[["Sarah Reed"], ["Maya Stone"], ["Maya Stone"]])
    out = cur.scrub(as_png(im))

    assert cur.located == 2
    assert any("masked" in c for c in out.changed)


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


# ------------------------------------------------------------- the row bound


@needs_fonts
def test_a_replacement_is_never_painted_onto_another_row():
    """The defect this exists for: a beneficiary's name from a table row was
    painted across the `View all activity ›` link at the foot of the table,
    leaving a stray `v` behind. Measured over five locate responses for the same
    capture, 5.1% of placements landed on a row other than the one the model
    pointed at, in four of the five.

    Matching cannot prevent it. Over those runs the in-row match errors ran
    0.115-0.599 and the crossing errors 0.450-0.579 — the two distributions sit
    on top of each other, so no tolerance tells them apart. The row bound is
    geometric and absolute.
    """
    im = shot([(10, 40, "Sarah Reed", 15),
               (10, 92, "View all activity", 15)])   # a control, one row down
    before = as_png(im)
    # A box pointing at the FIRST row. `View all activity` is a near-identical
    # width at the same height, so on width alone it is an equally good match.
    after, done = redact.paint(before, [{
        "text": "Sarah Reed", "kind": "person_name",
        "box": box_of(im, 10, 40, 82, 55), "replacement": "Maya Stone",
    }])

    with Image.open(io.BytesIO(before)) as b:
        control = [(x, y) for y in range(86, 112) for x in range(b.size[0])
                   if b.getpixel((x, y)) != (255, 255, 255)]
    assert control, "the control has to be there for the test to mean anything"
    assert not (differing(before, after) & set(control)), \
        "the substitution was painted over the control on the row below"


@needs_fonts
def test_a_value_the_model_pointed_at_the_wrong_row_is_masked_not_relocated():
    """There used to be a rescue pass here: where nothing matched on the box's
    own row it widened the band past the neighbouring rows and dropped the
    vertical anchor. It did recover boxes the model had put a row out — and it
    is also how the beneficiary reached the link. Masking on the row the model
    named is the honest answer: the mosaic is visible, it is where the model
    said to look, and the read-back pass catches the value if it was elsewhere.
    """
    im = shot([(10, 92, "Sarah Reed", 15)])     # the value is on the LOWER row
    before = as_png(im)
    after, done = redact.paint(before, [{
        "text": "Sarah Reed", "kind": "person_name",
        "box": box_of(im, 10, 40, 82, 55),      # the box points a whole row high
        "replacement": "Maya Stone",
    }])
    assert done and done[0].get("blurred") is True
    assert all(y < 86 for _x, y in differing(before, after)), \
        "it reached down and repainted the row it was not pointed at"


# --------------------------------------- values the locate pass never reported


def test_the_sweep_finds_money_and_email_the_model_did_not_report():
    """The verify step only re-checked values the model had already named, so a
    value it never named was never checked. Measured across five live runs of
    the same capture, the locate pass missed two of the activity table's payout
    amounts on one run and found them on the other four — recall varies run to
    run exactly as placement does."""
    from sparrow.agents.curator import _unlocated

    lines = ["Recent activity",
             "Payout  To Willow Ridge Farms  £58,170.32  Succeeded",
             "jamie.moore@novastores.com"]
    plan = [{"text": "£1,454.84"}]
    got = {f["text"] for f in _unlocated(lines, plan)}
    assert got == {"£58,170.32", "jamie.moore@novastores.com"}


def test_the_sweep_ignores_what_it_cannot_tell_from_product_chrome():
    """Ids, counts and version strings are deliberately out of scope. A sweep
    that fires on those masks the parts of the screenshot worth keeping — and
    the counters and API version are exactly what makes the capture read as
    real software."""
    from sparrow.agents.curator import _unlocated

    lines = ["231", "Refunded 7", "API v2025-05-16", "pay_01JTVX8Z8Q3K6Y6Z7J9X2V1F4P",
             "16 May, 14:31", "Step 3 of 6", "1 USD = 7.2213 CNY"]
    assert _unlocated(lines, []) == []


def test_a_value_already_substituted_is_not_swept_again():
    from sparrow.agents.curator import _unlocated

    assert _unlocated(["Gross volume £663,734.26"], [{"text": "£663,734.26"}]) == []


def test_the_sweep_does_not_report_the_values_the_scrub_itself_wrote():
    """The replacements are money-shaped by construction — that is the point of
    substituting rather than masking. A sweep that knows only the originals
    reads every amount it just substituted as an unlocated leak and masks the
    lot on the retry, which is the grey smear arriving by the back door."""
    from sparrow.agents.curator import _unlocated

    plan = [{"text": "£12,500.00", "replacement": "£58,170.32"},
            {"text": "sarah.reed@acmemarkets.com",
             "replacement": "jamie.moore@novastores.com"}]
    lines = ["Payout To Willow Ridge Farms £58,170.32 Succeeded",
             "jamie.moore@novastores.com"]
    assert _unlocated(lines, plan) == []


def test_a_survivor_is_recognised_when_the_two_reads_disagree():
    """Measured live: the locate pass transcribed a beneficiary as `Foo Food
    Suppliers Ltd` and the read-back returned `To Food Suppliers Ltd`. On an
    exact substring test the survivor check found nothing, and the row shipped
    unscrubbed while the report said it had been replaced."""
    from sparrow.agents.curator import _still_reads

    assert _still_reads("Foo Food Suppliers Ltd",
                        ["Payout", "To Food Suppliers Ltd", "£12,500.00"])
    assert _still_reads("£125,430.28", ["Gross volume", "£125,430.28"])


def test_a_substituted_row_does_not_read_as_a_survivor():
    """The check has to stay quiet on success, or every run masks everything."""
    from sparrow.agents.curator import _still_reads

    assert not _still_reads("Foo Food Suppliers Ltd",
                            ["Payout", "To Willow Ridge Farms", "£58,170.32"])
    assert not _still_reads("Sarah Reed", ["Jamie Moore", "Operations"])


@needs_fonts
def test_a_mask_covers_the_whole_value_not_just_the_box():
    """Measured on a live run: the model's box for a card's `•••• 4242` sat a
    few pixels left, the mask covered the bullets and the first digit, and `242`
    was left sitting in the open — three quarters of a card number."""
    im = shot([(10, 40, "•••• 4242", 15)])
    before = as_png(im)
    short = box_of(im, 8, 40, 40, 55)           # covers the bullets, not the digits
    after, done = redact.paint(before, [{
        "text": "4242", "kind": "identifier", "box": short, "replacement": "",
    }])
    assert done and done[0].get("blurred") is True
    with Image.open(io.BytesIO(before)) as b:
        ink = [x for x in range(b.size[0])
               if any(b.getpixel((x, y)) != (255, 255, 255) for y in range(35, 62))]
    xs = {x for x, _y in differing(before, after)}
    assert max(xs) >= max(ink), "the digits were left readable beside the mask"


@needs_fonts
def test_growing_a_mask_never_moves_it_off_its_row():
    im = shot([(10, 10, "Gross volume", 15),
               (10, 40, "•••• 4242", 15),
               (10, 70, "Successful", 15)])
    before = as_png(im)
    after, _done = redact.paint(before, [{
        "text": "4242", "kind": "identifier",
        "box": box_of(im, 8, 40, 40, 55), "replacement": "",
    }])
    ys = {y for _x, y in differing(before, after)}
    assert ys and min(ys) > 25 and max(ys) < 68

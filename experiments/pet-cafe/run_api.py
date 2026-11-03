"""pet-cafe: a real cat café's own material, through the office HTTP API.

Crumbs & Whiskers (crumbsandwhiskers.com, DC & LA) stands in for a local
business owner: its wordmark, eight of its photos and the facts on its home
page are the material; the brief says nothing else. Its own site is not a
reference. References are the hospitality sites the office network lets
through: catcafelounge.com (main), ladydinahs.com, headspace.com.

Driven entirely through the API the frontend uses — POST /projects, the
/advance SSE stream, GET/POST /gate, the upload endpoints — so this is the
path a real owner's run takes. Gates are answered as that owner: the name,
the first direction, every photo used as it is (they are already public), a
slot with no matching photo generated, no portrait or video, no answers to
invented facts (so they are retracted).

    cd backend && uv run python ../experiments/pet-cafe/run_api.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
API = os.environ.get("SPARROW_API", "http://localhost:8000")
PID = os.environ.get("CAFE_PID", "crumbs-whiskers")

BRIEF = dict(
    project_id=PID,
    product_name="Crumbs & Whiskers",
    category="Local business website — cat café",
    offering=(
        "Crumbs & Whiskers is DC & LA's first cat café: coffee and adoptable cats. "
        "Drink coffee, cuddle cats, save lives. It partners with local non-profit rescues "
        "to save cats and kittens at risk of euthanasia, then cares for them in its cafés "
        "until they are adopted into loving homes. 5,000+ adoptions and counting; 10,000+ "
        "cats saved from euthanasia; $60K+ donated to animal causes. 100% of proceeds from "
        "its merch go to the Cat Health Fund, which provides medical care for every cat in "
        "the cafés. Founded by Kanchan, who started it after visiting a cat café in "
        "Thailand. Cafés in Los Angeles and Washington DC. Visitors book tickets for a "
        "visit; anyone can support the cats, shop merch and follow the cats online."),
    audience=(
        "Cat lovers, couples and friends looking for a feel-good outing in LA or DC, and "
        "people thinking about adopting a cat."),
    tone="Warm, playful and heartfelt — joyful about the cats, sincere about the rescue mission.",
    primary_action="Book tickets",
    secondary_action="Support our cats",
    constraints=[
        "do not invent prices, opening hours, addresses, reviews, testimonials, cat names "
        "or partner organisation names",
    ],
    urls=["https://www.catcafelounge.com/", "https://www.ladydinahs.com/",
          "https://www.headspace.com/"],
    main_reference="https://www.catcafelounge.com/",
)

# The owner's files, what each shows (the caption), and the words that place it.
PHOTOS = [
    ("photo-4.jpg", "A guest holding two cats in front of the Crumbs & Whiskers neon sign "
                    "and flower wall", "hero welcome visit guests neon interior"),
    ("photo-3.png", "A collage of the cafés: cats, guests and the neon-sign interiors",
     "gallery collage interior cafe space"),
    ("photo-7.jpg", "A guest lying on the cushions with a black cat beside him",
     "visit experience relax guests lounge"),
    ("photo-2.png", "A guest cuddling a ragdoll cat on the white sofa",
     "adopt adoption cuddle guest cat"),
    ("photo-8.jpg", "Patty, a black-and-white cat, on a cat tree in the café",
     "cat resident adoptable meet"),
    ("photo-5.jpg", "A tabby cat with a pink bow tie on a cat tree", "cat adoptable rescue"),
    ("photo-6.jpg", "A black cat dressed up as a doctor — the Cat Health Fund",
     "health fund donate support medical"),
    ("merch-sweatshirt.jpg", "A pink Crumbs & Whiskers sweatshirt from the merch shop",
     "merch shop store sweatshirt"),
]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def advance(c: httpx.Client, stages: dict) -> None:
    """Run to the next gate, logging the stream."""
    with c.stream("POST", f"/projects/{PID}/advance", timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            e = json.loads(line[6:])
            stages.setdefault(e.get("stage"), time.time())
            k = e.get("kind")
            if k in ("done", "failed", "awaiting", "blocked", "stopped") or e.get("cost") \
                    or e.get("stage") in ("assets", "build", "verify"):
                log(f"{e.get('stage')} · {k} · {str(e.get('message'))[:200]}"
                    + (f" · ${e['cost']:.3f}" if e.get("cost") else ""))
            if k == "failed":
                raise SystemExit(f"failed: {e.get('message')}")


def score(option: dict, words: str) -> int:
    text = f"{option.get('section_id', '')} {option.get('brief', '')}".lower()
    return sum(w in text for w in words.split())


def answer_assets(c: httpx.Client, gate: dict) -> None:
    # Every question that is not about a fact: images, the logo, any video.
    images = [o for o in gate["options"] if o.get("kind") != "fact"]
    plan = c.get(f"/projects/{PID}/assets").json()
    left = list(PHOTOS)
    decisions: dict[str, str] = {}
    for o in sorted(images, key=lambda o: o.get("section_id") != "hero"):
        aid, choices = o["asset_id"], {ch["choice"] for ch in o.get("choices", [])}
        if "wordmark" in choices or aid.endswith("logo"):
            with open(ASSETS / "wordmark.png", "rb") as f:
                c.post(f"/projects/{PID}/assets/{aid}",
                       files={"file": ("wordmark.png", f, "image/png")}).raise_for_status()
            decisions[aid] = "upload"
        elif "generate" not in choices or not left:
            # a portrait (never generated) or a video: the owner has neither
            decisions[aid] = "skip" if "skip" in choices else "generate"
        else:
            best = max(left, key=lambda p: score(o, p[2]))
            left.remove(best)
            with open(ASSETS / best[0], "rb") as f:
                c.post(f"/projects/{PID}/assets/{aid}",
                       files={"file": (best[0], f)}).raise_for_status()
            decisions[aid] = "as_is"
            log(f"  {aid} ← {best[0]}")
        log(f"  {aid} ({o.get('section_id')}): {decisions[aid]} · {o.get('brief', '')[:80]}")
    extras = [a for a in plan if a.get("extra")]
    for name, caption, _ in left:
        prior = next((a for a in extras if a.get("brief") == caption), None)
        if prior:   # added by an earlier attempt at this gate
            decisions[prior["id"]] = "as_is"
            log(f"  {prior['id']}: as_is ← {name} (already added)")
            continue
        with open(ASSETS / name, "rb") as f:
            r = c.post(f"/projects/{PID}/owner-images", data={"caption": caption},
                       files={"file": (name, f)})
        r.raise_for_status()
        decisions[r.json()["asset_id"]] = "as_is"
        log(f"  {r.json()['asset_id']}: as_is ← {name} · {caption}")
    r = c.post(f"/projects/{PID}/gate", json={"assets": decisions, "content": {}})
    if r.status_code >= 400:
        raise SystemExit(f"asset gate refused: {r.text}")
    log(f"gate:assets → {len(decisions)} decision(s)")


def main() -> None:
    t0 = time.time()
    stages: dict = {}
    with httpx.Client(base_url=API, timeout=120) as c:
        if c.get(f"/projects/{PID}").status_code == 404:
            c.post("/projects", json=BRIEF).raise_for_status()
            log(f"created {PID}")
        while True:
            advance(c, stages)
            gate = c.get(f"/projects/{PID}/gate").json()
            if not gate.get("awaiting"):
                break
            g = gate["gate"]
            if g == "gate:brief":
                c.post(f"/projects/{PID}/gate",
                       json={"product_name": BRIEF["product_name"]}).raise_for_status()
                log(f"gate:brief → {BRIEF['product_name']}")
            elif g == "gate:design":
                c.post(f"/projects/{PID}/gate", json={"choice": 0}).raise_for_status()
                log("gate:design → direction 0")
            elif g == "gate:assets":
                answer_assets(c, gate)
            else:
                log(f"{g}: {gate.get('question', '')[:400]}")
                break
        info = c.get(f"/projects/{PID}").json()
    out = {"seconds": round(time.time() - t0), "spent_usd": info.get("spent"),
           "stage_started_at": stages, "preview": f"http://localhost:3000/projects/{PID}/preview/"}
    (HERE / f"run-{PID}.json").write_text(json.dumps(out, indent=2))
    log(json.dumps({k: v for k, v in out.items() if k != "stage_started_at"}))


if __name__ == "__main__":
    sys.exit(main())

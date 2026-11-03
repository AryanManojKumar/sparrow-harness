"""BUILD and VERIFY when the agent designs the site.

Experiment dsh-builder-02 (RESULTS.md) settled who designs. Sparrow's builder
built what its composer planned, section by section, and the plan was the
weaker design; a free agent designing from the references looked best but took
a reference's red, invented facts and ignored the curated material. B+ — the
free agent, held by Sparrow's material and guardrails — kept the looks and
fixed all three. This module is B+ in the pipeline:

- Sparrow keeps everything upstream: the brief, the scouted references, the
  copy with its provenance, the material gate and the curated assets.
- ASSETS settles the copy, then the images are made in the background while
  the agent builds on placeholders of the final size (`step_assets`). They
  are swapped in when ready and the agent looks at the real page.
- BUILD hands that to the studio agent in the workshop — references as `refs/`,
  facts and assets in the dossier — and the agent designs and builds the site
  in one studio turn (edit → build → look → polish). From then on the workshop
  holds the site, so the studio carries on from the same copy.
- VERIFY runs Sparrow's guardrails (`guard`) on what came back. Findings go to
  the agent as a fix turn, at most `FIX_ROUNDS` times (§8: loops cap), and the
  run stops at the preview gate whatever happened.

The composer's per-section plan is not on this path. Its measurements are still
on disk for anyone who wants them as reference.

Selected by `SPARROW_BUILDER` — `agent` (default) or `sections` for the old
builder.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path

from sparrow.blackboard.schema import Blackboard
from sparrow.orchestrator import Event, GateRequest, Halt, Run, Stage

MARK = "agent-build.json"
FIX_ROUNDS = 2

BUILD_PROMPT = """Build a complete marketing website for {name}.

What it is: {offering}
Who it is for: {audience}
Tone: {tone}
Main action: {primary}.{secondary}

Reference sites — screenshots of each are in refs/, top to bottom: {sites}. Look at them \
before you design anything; the site should look like it belongs beside them.

Use the curated images and video listed in AGENTS.md — they were made for this product. \
Everything you may state is in AGENTS.md; invent nothing beyond it. Learn layout, pacing \
and craft from the references, but give the product its own look: never reproduce a \
reference's brand — its signature colours, logo treatment or distinctive type."""


def enabled() -> bool:
    return (os.environ.get("SPARROW_BUILDER") or "agent").lower() == "agent"


def agent_designed(project_dir: Path) -> bool:
    return (project_dir / MARK).is_file()


def references(project_dir: Path) -> list[str]:
    """The reference URLs, the main one first."""
    try:
        urls = json.loads((project_dir / "urls.json").read_text())
    except (OSError, ValueError):
        return []
    p = project_dir / "sources" / "primary.txt"
    primary = p.read_text().strip() if p.is_file() else ""
    return sorted(urls, key=lambda u: not (primary and primary in u))


def stage_refs(run: Run) -> int:
    """The reference bands and sheets into `refs/` (outside git, outside the export)."""
    refs = run.workspace / "refs"
    shutil.rmtree(refs, ignore_errors=True)
    refs.mkdir(parents=True)
    n = 0
    for f in sorted((run.dir / "sources").glob("*.png")):
        if re.search(r"-(b\d+|sheet)\.png$", f.name):
            shutil.copy(f, refs / f.name)
            n += 1
    return n


def direction_note(bb: Blackboard) -> str:
    """The direction the owner chose at gate 2, as a starting point.

    The owner picked it, and the curated imagery was generated in it — so the
    agent is told, but not held: type, layout and the final palette are its own.
    """
    ds = bb.design_system
    if ds is None:
        return ""
    cols = ", ".join(f"{c.name} `{c.value}`" for c in ds.colors[:9])
    # Motion and treatments were dropped here at first, and twenty-crm shipped
    # with no movement at all against a direction that specified a live canvas
    # and 200ms transitions: the agent was never told.
    treat = "".join(f"\n- **{t.name}**: where: {t.where}; how: {t.how}" for t in ds.treatments)
    return ("\n## The direction the owner chose\n\n"
            f"{ds.atmosphere}\n\nIts colours: {cols}. The curated imagery was made in this "
            "direction. Start from it; type, layout, composition and the final palette are "
            "yours.\n"
            + (f"\nIts motion, to build, not to describe: {ds.motion}\n" if ds.motion else "")
            + (f"\nHow each section arrives as the reader reaches it, to build: "
               f"{ds.arrival}\n" if ds.arrival else "")
            + (f"\nIts surface treatments (each in its place, not spread across the page):"
               f"{treat}\n" if treat else ""))


def source_motion(run: Run) -> tuple[str, dict | None]:
    """The scout's MOTION block from the design brief, and its arrival numbers.

    The block is the scout's measurement of the reference sites, already
    written for an agent to read; the numbers are parsed back out of it so the
    check holds the page to the same figures the agent was shown.
    """
    f = run.dir / "sources" / "design-brief.md"
    text = f.read_text() if f.is_file() else ""
    m = re.search(r"^ *MOTION\n(.*?)(?=^ *[A-Z][A-Z /&-]{3,}\n|\Z)", text, re.M | re.S)
    if not m:
        return "", None
    block = m.group(1).rstrip()
    share = re.search(r"(\d+)% of all elements are staged", block)
    if not share:
        return block, None
    num = lambda pat, d: (lambda x: float(x.group(1)) if x else d)(re.search(pat, block))
    return block, {"share": int(share.group(1)) / 100,
                   "from": num(r"start at opacity ([\d.]+)", 1.0),
                   "travel": int(num(r"rise (\d+)px", 0)), "ms": int(num(r"over (\d+)ms", 0))}


def motion_note(run: Run) -> str:
    block, _ = source_motion(run)
    return (f"\nHow the reference sites move (measured on the live pages):\n\n{block}\n"
            if block else "")


def scale_note(run: Run) -> str:
    ref = reference_scale(run)
    if not ref:
        return ""
    return (f"\nThe main reference, {ref[0]}, sets its largest heading at {round(ref[1])}px "
            "(measured).\n")


def dossier_for(run: Run, bb: Blackboard | None = None) -> str:
    from sparrow import dossier, steps

    bb = bb or steps._bb(run)
    text = dossier.render(bb, steps.load_content(run), steps.preview_base(run),
                          references=references(run.dir))
    note = direction_note(bb) + motion_note(run) + scale_note(run)
    if note and "## Build rules" in text:
        i = text.index("## Build rules")
        text = text[:i] + note.lstrip("\n") + "\n" + text[i:]
    return text


def build_prompt(run: Run, bb: Blackboard) -> str:
    b = bb.brief
    sites = references(run.dir)
    return BUILD_PROMPT.format(
        name=b.product_name or run.project_id, offering=b.offering, audience=b.audience,
        tone=b.tone, primary=b.primary_action,
        secondary=f" Secondary action: {b.secondary_action}." if b.secondary_action else "",
        sites=", ".join(u + (" (the main reference)" if i == 0 else "")
                        for i, u in enumerate(sites)) or "see refs/")


def describe(e: dict) -> str | None:
    """One studio event as a run-log line."""
    k = e.get("kind")
    if k == "tool":
        return f"{e.get('tool')} {e.get('target', '')}".strip() + (
            f" · {e['detail']}" if e.get("detail") else "")
    if k == "tool_result" and not e.get("ok"):
        return f"  ✗ {e.get('summary', '')[:200]}"
    if k in ("status", "note"):
        return str(e.get("text", ""))[:300]
    return None


def _turn(run: Run, message: str, stage: Stage, look: bool = True,
          fresh: bool = False, look_only: bool = False) -> Iterator[Event | dict]:
    """Stream one studio turn as Events; the last item yielded is the turn's end."""
    from sparrow import gateway
    from sparrow.workshop.client import Workshop

    ws = Workshop()
    t0 = time.time()
    end: dict | None = None
    for e in ws.turn(run.project_id, message, gateway.TOKENS.issue(run.project_id),
                     look=look, fresh=fresh, **({"look_only": True} if look_only else {})):
        if e.get("kind") in ("done", "error"):
            end = e
            continue
        line = describe(e)
        if line:
            yield Event(stage, "progress", line, {"studio": e})
    used = gateway.usage_since(run.project_id, t0)
    yield Event(stage, "progress",
                f"agent: {used['calls']} model call(s), {used['input']:,} tokens in "
                f"({used['cached']:,} cached), {used['output']:,} out",
                {"usage": used}, cost=used["cost"])
    yield end or {"kind": "error", "text": "the turn ended without an answer"}


# ── assets, made while the agent builds ─────────────────────────────────────
#
# Measured on sparrow-ide-v4: 2 min 46 s of image generation, then a 5 minute
# build that only needed the images' paths and sizes. Both are known from the
# plan before anything is generated (`public/assets/{id}.png`, the provider's
# fixed shapes, an upload's own size), so the build starts on stand-ins and the
# agent looks once the real files are in.

_BACKGROUND: dict[str, dict] = {}


def _stand_in(path: Path, size: tuple[int, int], colour: str) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        Image.new("RGB", size, colour).save(path)
    except ValueError:
        Image.new("RGB", size, "#9aa0a6").save(path)


def _stand_in_video(path: Path, size: tuple[int, int]) -> bool:
    import subprocess

    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"color=c=gray:s={size[0]}x{size[1]}:d=2", "-pix_fmt", "yuv420p",
                        str(path)], check=True, timeout=30)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def placeholders(run: Run, bb: Blackboard) -> list[str]:
    """Stand-ins for every asset still to be made, recorded as the assets.

    Returns the ids that are stand-ins. A logo or video the owner uploaded is
    only a copy, so it is put in place for real; an asset already produced is
    kept as it is.
    """
    from PIL import Image

    from sparrow import steps
    from sparrow.agents.curator import _SIZES, derive_variants
    from sparrow.blackboard.schema import Asset, AssetKind, Prominence, Provenance

    public = run.workspace / "public"
    done = {a.id: a for a in bb.assets if (public / a.path).exists()}
    colour = next((c.value for c in (bb.design_system.colors if bb.design_system else [])
                   if re.search(r"muted|surface|subtle|panel", c.name, re.I)), "#9aa0a6")
    wide = _wide_size(_SIZES)
    records: list[Asset] = []
    stand_ins: list[str] = []
    for a in steps.resolved_plan(run):
        aid, decision, kind = a["id"], a.get("decision") or "generate", steps._kind(a)
        if decision == "skip" or (kind == "logo" and decision == "wordmark"):
            continue
        if aid in done and done[aid].kind.value == kind:
            records.append(done[aid])
            continue
        base = dict(id=aid, section_id=a["section_id"], brief=a["brief"],
                    prominence=Prominence(a["prominence"]))
        upload = run.dir / "uploads" / a["upload"] if a.get("upload") else None
        if upload is not None and decision == "upload" and kind in ("logo", "video"):
            dest = public / "assets" / f"{aid}{upload.suffix.lower() if kind == 'logo' else upload.suffix}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(upload.read_bytes())
            w, h = steps._logo_size(dest) if kind == "logo" else (0, 0)
            records.append(Asset(**base, kind=AssetKind(kind), provenance=Provenance.USER_SUPPLIED,
                                 path=f"assets/{dest.name}", width=w, height=h))
            continue
        if a["brief"].lstrip().lower().startswith("[video]") or kind == "video":
            dest = public / "assets" / f"{aid}.mp4"
            dest.parent.mkdir(parents=True, exist_ok=True)
            _stand_in_video(dest, (1280, 720))
            records.append(Asset(**base, kind=AssetKind.VIDEO, provenance=Provenance.GENERATED,
                                 path=f"assets/{dest.name}", width=1280, height=720))
            stand_ins.append(aid)
            continue
        if upload is not None and decision == "as_is":
            # The owner's word that it is public: shipped untouched, so a copy now.
            dest = public / "assets" / f"{aid}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            steps._write_png(upload.read_bytes(), dest, Image)
            with Image.open(dest) as im:
                w, h = im.size
            # No `--` crops: an owner's published image is composed — on
            # twenty-crm each carried its own title, and a centre crop kept
            # the title and cut the product.
            records.append(Asset(
                **base, kind=AssetKind.IMAGE, provenance=Provenance.USER_SUPPLIED,
                path=f"assets/{dest.name}", width=w, height=h))
            continue
        size = wide
        if upload is not None and upload.is_file():
            try:
                with Image.open(upload) as im:
                    size = im.size
            except OSError:
                pass
        dest = public / "assets" / f"{aid}.png"
        _stand_in(dest, size, colour)
        records.append(Asset(
            **base, kind=AssetKind.PORTRAIT if kind == "portrait" else AssetKind.IMAGE,
            provenance=Provenance.USER_SUPPLIED if upload is not None else Provenance.GENERATED,
            path=f"assets/{dest.name}", width=size[0], height=size[1],
            variants={k: f"assets/{v}" for k, v in derive_variants(dest).items()}))
        stand_ins.append(aid)
    (run.dir / steps.PENDING_ASSETS).write_text(json.dumps(stand_ins))
    bb.assets = records
    steps._replace(run, "/assets", [r.model_dump(mode="json") for r in records],
                   agent="curator", summary=f"{len(stand_ins)} placeholder(s) while the "
                                            "images are made")
    return stand_ins


def _wide_size(sizes: dict) -> tuple[int, int]:
    """The pixel size a generated "wide" image comes back at."""
    v = sizes.get("wide")
    if isinstance(v, (tuple, list)) and len(v) == 2:
        return int(v[0]), int(v[1])
    if isinstance(v, str) and ":" in v:
        w, h = (int(x) for x in v.split(":"))
        return 1536, round(1536 * h / w)
    return 1536, 1024


def _background(run: Run) -> None:
    """Run the real ASSETS stage on its own thread; events wait in a queue."""
    import contextvars
    import queue

    from sparrow import steps

    q: queue.Queue = queue.Queue()
    job = {"queue": q, "error": None}

    def work() -> None:
        try:
            for ev in steps.step_assets(run):
                q.put(ev)
        except Exception as e:  # noqa: BLE001 — reported when the build collects it
            job["error"] = f"{type(e).__name__}: {e}"
        finally:
            q.put(None)

    job["thread"] = threading.Thread(target=contextvars.copy_context().run, args=(work,),
                                     daemon=True)
    _BACKGROUND[run.project_id] = job
    job["thread"].start()


def step_assets(run: Run) -> Iterator[Event]:
    """ASSETS when the agent builds: settle the copy, start the images, move on."""
    from sparrow import steps

    yield from steps._retract_unanswered_claims(run)
    stand_ins = placeholders(run, steps._bb(run))
    if not stand_ins:
        (run.dir / steps.PENDING_ASSETS).unlink(missing_ok=True)
        yield Event(Stage.ASSETS, "done", "nothing to make — the build starts now")
        return
    _background(run)
    yield Event(Stage.ASSETS, "done",
                f"{len(stand_ins)} image(s) being made while the agent builds — it starts "
                "on placeholders of the final size")


def collect_assets(run: Run) -> Iterator[Event]:
    """Wait for the background images and relay what happened.

    A restart loses the thread; the stand-ins are still on disk and marked, so
    the stage simply runs here instead.
    """
    from sparrow import steps

    if not steps.pending_assets(run):
        return
    job = _BACKGROUND.pop(run.project_id, None)
    if job is None:
        events = steps.step_assets(run)
    else:
        def drain():
            while (ev := job["queue"].get()) is not None:
                yield ev
            if job["error"]:
                raise RuntimeError(job["error"])
        events = drain()
    try:
        for ev in events:
            yield Event(Stage.ASSETS, "progress" if ev.kind == "done" else ev.kind,
                        ev.message, ev.data, cost=ev.cost)
    except Exception as e:  # noqa: BLE001 — the build stands; the look turn is told
        yield Event(Stage.ASSETS, "blocked", f"images failed: {type(e).__name__}: {e}"[:400])


SWAPPED = """The real images are now in place of the placeholders you built with — same paths, same sizes.{missing} Look at the page with them in and fix anything they made wrong: contrast with text over them, crops that cut the important part, framing."""


def _still_stand_in(f: Path) -> bool:
    """A stand-in is one flat colour; a made image never is."""
    from PIL import Image

    if not f.is_file():
        return True
    if f.suffix != ".png":
        return False
    try:
        with Image.open(f) as im:
            return all(lo == hi for lo, hi in im.convert("RGB").getextrema())
    except OSError:
        return True


def swap_in(run: Run, stand_ins: list[str]) -> list[str]:
    """Send the real files over the stand-ins. Returns the ids never made.

    Judged by the file, not the record: a stage that failed half way has
    checkpointed some records and left others as the stand-ins wrote them.
    """
    from sparrow import steps
    from sparrow.workshop.client import Workshop

    ws = Workshop()
    bb = steps._bb(run)
    public = run.workspace / "public"
    missing: list[str] = []
    for a in (a for a in bb.assets if a.id in stand_ins):
        if _still_stand_in(public / a.path):
            continue
        for rel in [a.path, *a.variants.values()]:
            f = public / rel
            if f.is_file():
                ws.put_asset(run.project_id, f.name, f.read_bytes(), replace=True)
    got = {a.id for a in bb.assets if not _still_stand_in(public / a.path)}
    missing = [aid for aid in stand_ins if aid not in got]
    ws.put_dossier(run.project_id, dossier_for(run, bb))
    return missing

def step_build(run: Run) -> Iterator[Event]:
    from sparrow import steps
    from sparrow.workshop.client import Workshop

    bb = steps._bb(run)
    if not (run.workspace / "package.json").is_file():
        raise RuntimeError("no workspace to build in — the scaffold was never copied")
    n = stage_refs(run)
    ws = Workshop()
    # A fresh push every time BUILD runs: the pipeline only reaches BUILD before
    # the studio has taken the site over (`api._not_in_studio` refuses after).
    ws.push(run.project_id, run.workspace)
    ws.put_dossier(run.project_id, dossier_for(run, bb))
    (run.dir / MARK).write_text(json.dumps({"started_at": time.time()}))
    stand_ins = sorted(steps.pending_assets(run))
    yield Event(Stage.BUILD, "progress",
                f"handed to the agent: {n} reference band(s), {len(bb.assets)} curated "
                f"asset(s), {len(bb.active_constraints())} hard rule(s)"
                + (f" · {len(stand_ins)} still being made" if stand_ins else ""))

    end: dict = {}
    # With stand-ins in place there is nothing worth looking at yet: the look
    # comes after the swap, in the same conversation.
    for item in _turn(run, build_prompt(run, bb), Stage.BUILD, look=not stand_ins):
        if isinstance(item, Event):
            yield item
        else:
            end = item
    if end.get("kind") == "error" or end.get("reverted") or not end.get("checkpoint"):
        raise RuntimeError("the agent did not produce a site that builds: "
                           + str(end.get("text") or end.get("reply") or "no change")[:300])

    if stand_ins:
        yield Event(Stage.BUILD, "progress", "waiting for the images")
        yield from collect_assets(run)
        missing = swap_in(run, stand_ins)
        note = (f" These could not be made and their files are blank placeholders — take "
                f"them off the page: {', '.join(missing)}." if missing else "")
        yield Event(Stage.BUILD, "progress",
                    f"real images swapped in ({len(stand_ins) - len(missing)} of "
                    f"{len(stand_ins)}) — the agent looks at the page")
        looked: dict = {}
        for item in _turn(run, SWAPPED.format(missing=note), Stage.BUILD, look_only=True):
            if isinstance(item, Event):
                yield item
            else:
                looked = item
        if looked.get("kind") == "error":
            # The site built and the images are in it; only the look failed.
            yield Event(Stage.BUILD, "progress",
                        f"the look after the images did not run: {looked.get('text', '')}"[:300])
    # From here the workshop's copy is the live one: the preview proxies to it
    # and the studio continues from it. Written only now, so a failed build can
    # be advanced again (`api._not_in_studio` refuses a project in the studio).
    (run.dir / "studio.json").write_text(json.dumps(
        {"handed_over_at": time.time(), "workshop": ws.url}))
    yield Event(Stage.BUILD, "done", str(end.get("reply") or "site built")[:400],
                {"changed": end.get("changed", []), "checkpoint": end.get("checkpoint")})


# ── verify ──────────────────────────────────────────────────────────────────

def _pull(run: Run, into: Path) -> Path:
    import io
    import tarfile

    from sparrow.workshop.client import Workshop

    data = Workshop().pull(run.project_id)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(into, filter="data")
    return into


def _palettes(run: Run) -> dict:
    p = run.dir / "sources" / "palettes.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def findings(run: Run, bb: Blackboard) -> list:
    """Every guardrail, on the workshop's current copy of the site."""
    from sparrow import brand, guard, steps
    from sparrow.workshop.client import Workshop

    ws = Workshop()
    with tempfile.TemporaryDirectory(prefix="sparrow-verify-") as tmp:
        site = _pull(run, Path(tmp))
        curated = [Path(a.path).name for a in bb.assets
                   if (site / "public" / a.path).is_file() and a.kind.value != "logo"]
        out = guard.check_claims(site, confirmed(run, bb))
        out += guard.check_assets(site, curated)
    out += guard.check_links(ws.links(run.project_id))
    shots = [base64.b64decode(s["data"]) for s in ws.shots(run.project_id, "/")]
    out += guard.check_brand(brand.too_close(shots, _palettes(run)))
    page = ws.measure(run.project_id, "/")
    out += guard.check_crops(page.get("images", []),
                             {Path(a.path).name: (a.width, a.height) for a in bb.assets
                              if a.kind.value == "image" and a.width and a.height})
    out += guard.check_covered(page.get("covered", []))
    out += guard.check_arrival(page.get("arrival") or {}, source_motion(run)[1])
    if bb.design_system and bb.design_system.motion:
        with tempfile.TemporaryDirectory(prefix="sparrow-motion-") as tmp:
            out += guard.check_motion(_pull(run, Path(tmp)), bb.design_system.motion)
    out += guard.check_type(page.get("headings", []), reference_scale(run))
    return out


def reference_scale(run: Run) -> tuple[str, float] | None:
    """The main reference's largest measured heading: (site, px)."""
    try:
        typo = json.loads((run.dir / "typography.json").read_text())
    except (OSError, ValueError):
        return None
    p = run.dir / "sources" / "primary.txt"
    site = p.read_text().strip() if p.is_file() else ""
    roles = typo.get(site) or {}
    sizes = [float(r["size"]) for r in roles.values() if isinstance(r, dict) and r.get("size")]
    return (site, max(sizes)) if sizes else None


def confirmed(run: Run, bb: Blackboard) -> set[str]:
    """Words the page may state as fact: the brief, the constraints and the
    copy the OWNER supplied — not the copy the content stage drafted.

    `steps.confirmed_words` counts drafted slots too, because there the gate
    had already asked about each invention. On the first live agent build that
    let "Steam", "PlayStation" and "Discord" through: the content stage drafted
    them as footer badges and the gate was passed without confirming them. A
    drafted slot is wording to start from, never a fact.

    Plus the product name's own parts: a page that sets "MananShooter" as
    MANAN / SHOOTER is still naming the product, and "Manan" alone cost a whole
    fix round on that run."""
    from sparrow import steps
    from sparrow.audit import corpus_words

    b = bb.brief
    texts = [b.product_name or "", b.category or "", b.offering or "", b.audience or "",
             b.tone or "", b.primary_action or "", b.secondary_action or ""] if b else []
    texts += [c.text for c in bb.active_constraints()]
    for e in steps.load_content(run).values():
        prov = e.get("provenance") or {}
        for k, v in (e.get("slots") or {}).items():
            if prov.get(k) == "user_supplied":
                texts += v if isinstance(v, list) else [str(v)]
    words = corpus_words(*map(str, texts))
    name = (bb.brief.product_name if bb.brief else "") or ""
    words |= {w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", name)}
    return words


# What the agent is sent back to fix, and what the owner is shown instead.
#
# Links, assets and brand distance are certain: the check is exact and the fix
# is mechanical. Claims are not. On the first B2B run the claim check could not
# tell a made-up latency in a drawn dashboard from a tab label, and the round
# that chased both cost $5.63 — more than the build — while the next round went
# entirely on "Details", "Logs" and "Overview". A person decides those in
# seconds; the gate shows them, and the studio can act on the answer.
AUTO_FIX = {"link", "missing-asset", "unused-asset", "brand", "crop", "covered", "motion", "arrival", "type"}


def step_verify(run: Run) -> Iterator[Event]:
    from sparrow import guard, steps

    bb = steps._bb(run)
    rounds_path = run.dir / "verify-rounds.json"
    try:
        spent = int(json.loads(rounds_path.read_text()).get("spent", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        spent = 0

    found = findings(run, bb)
    fixable = [f for f in found if f.kind in AUTO_FIX]
    declined: list = []
    while fixable and spent < FIX_ROUNDS:
        yield Event(Stage.VERIFY, "progress",
                    f"{len(fixable)} finding(s) to fix: "
                    + "; ".join(f"{f.kind} ({f.where})" for f in fixable[:8]),
                    {"findings": guard.as_dicts(fixable)})
        spent += 1
        rounds_path.write_text(json.dumps({"spent": spent}))
        end: dict = {}
        for item in _turn(run, guard.fix_prompt(fixable), Stage.VERIFY,
                          look=False, fresh=True):
            if isinstance(item, Event):
                yield item
            else:
                end = item
        if end.get("kind") == "error":
            yield Event(Stage.VERIFY, "blocked", f"fix turn failed: {end.get('text', '')[:200]}")
            break
        before = {f.line() for f in fixable}
        found = findings(run, bb)
        fixable = [f for f in found if f.kind in AUTO_FIX]
        if before == {f.line() for f in fixable}:
            # The agent read every finding and changed none of them: it has
            # judged them wrong. A second identical round is the oscillation
            # §8 caps — stop here.
            declined = fixable
            yield Event(Stage.VERIFY, "progress",
                        f"the agent left {len(fixable)} finding(s) as they are — not asking again")
            break

    rounds_path.unlink(missing_ok=True)
    claims = [f for f in found if f.kind not in AUTO_FIX]
    left = guard.as_dicts(fixable)
    (run.dir / "verify-findings.json").write_text(json.dumps(
        {"unfixed": left, "for_owner": guard.as_dicts(claims)}, indent=1))
    yield Event(Stage.VERIFY, "done",
                f"{len(left)} finding(s) left after {spent} fix round(s)"
                + (f" · {len(claims)} possible claim(s) for the owner" if claims else ""),
                {"findings": left, "for_owner": guard.as_dicts(claims)})
    words = sorted({w.strip() for f in claims
                    for w in f.detail.split(": ", 1)[-1].split(". ", 1)[0].split(",")})
    raise Halt(GateRequest(
        Stage.GATE_PREVIEW,
        "The site is built. "
        + (f"{len(left)} check(s) still flag something"
           + (" (the agent looked and judged them fine)" if declined else "") + ": "
           + "; ".join(f"{f['kind']} — {f['detail'][:120]}" for f in left[:4]) + ". "
           if left else "Every automatic check passed. ")
        + (f"Check these words on the page — if any is a name, number or fact you did "
           f"not give us, remove it in the studio: {', '.join(words[:20])}. " if words else "")
        + "Ship it, or keep editing in the studio?",
        options=[{"choice": "approve", "label": "Looks good — publish"},
                 {"choice": "revise", "label": "Send it back with a note",
                  "needs_note": True}],
        artifacts=[str(run.workspace / "out")],
    ))

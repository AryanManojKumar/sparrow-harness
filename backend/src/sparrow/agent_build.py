"""BUILD and VERIFY when the agent designs the site.

Experiment dsh-builder-02 (RESULTS.md) settled who designs. Sparrow's builder
built what its composer planned, section by section, and the plan was the
weaker design; a free agent designing from the references looked best but took
a reference's red, invented facts and ignored the curated material. B+ — the
free agent, held by Sparrow's material and guardrails — kept the looks and
fixed all three. This module is B+ in the pipeline:

- Sparrow keeps everything upstream: the brief, the scouted references, the
  copy with its provenance, the material gate and the curated assets.
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
    return ("\n## The direction the owner chose\n\n"
            f"{ds.atmosphere}\n\nIts colours: {cols}. The curated imagery was made in this "
            "direction. Start from it; type, layout, composition and the final palette are "
            "yours.\n")


def dossier_for(run: Run, bb: Blackboard | None = None) -> str:
    from sparrow import dossier, steps

    bb = bb or steps._bb(run)
    text = dossier.render(bb, steps.load_content(run), steps.preview_base(run),
                          references=references(run.dir))
    note = direction_note(bb)
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
          fresh: bool = False) -> Iterator[Event | dict]:
    """Stream one studio turn as Events; the last item yielded is the turn's end."""
    from sparrow import gateway
    from sparrow.workshop.client import Workshop

    ws = Workshop()
    t0 = time.time()
    end: dict | None = None
    for e in ws.turn(run.project_id, message, gateway.TOKENS.issue(run.project_id),
                     look=look, fresh=fresh):
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
    yield Event(Stage.BUILD, "progress",
                f"handed to the agent: {n} reference band(s), {len(bb.assets)} curated "
                f"asset(s), {len(bb.active_constraints())} hard rule(s)")

    end: dict = {}
    for item in _turn(run, build_prompt(run, bb), Stage.BUILD):
        if isinstance(item, Event):
            yield item
        else:
            end = item
    if end.get("kind") == "error" or end.get("reverted") or not end.get("checkpoint"):
        raise RuntimeError("the agent did not produce a site that builds: "
                           + str(end.get("text") or end.get("reply") or "no change")[:300])
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
    return out


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
AUTO_FIX = {"link", "missing-asset", "unused-asset", "brand"}


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

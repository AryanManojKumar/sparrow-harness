"""The stage implementations the orchestrator drives.

Each is a generator yielding `Event`s, so a caller sees progress during a stage
that takes minutes. Each raises `Halt` at a gate.

These wrap the same agents the CLI has been calling by hand all along; nothing
here is new capability. What is new is that the ORDER is written down once,
rather than living in whoever is typing the commands.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

from sparrow.blackboard.schema import (GROUND_PAGE, AssetKind, Blackboard, BuildStatus,
                                       Section)
from sparrow.blackboard.store import Rejected, Store
from sparrow.orchestrator import Event, GateRequest, Halt, Run, Stage

# The footer only. `nav` came OFF this list once the logo had a real path
# through the material gate: the reason nav was skipped was that its blueprint
# asks for "the company wordmark", the curator generated one, and a 1536x1024
# "logo lockup" came back and was rendered at DOMINANT prominence — a full-width
# blank box above the hero, which is what "the site looks broken" turned out to
# mean. That reason is now handled by ROUTING rather than by exclusion: nav's
# blueprint asset briefs are replaced by one LOGO entry (see `asset_plan`), and
# a logo can only be uploaded or set as a wordmark. There is no path from nav to
# `Curator.generate` at all.
#
# The footer stays excluded because it carries the SAME mark as the nav. One
# logo, one entry, asked once — not the same question twice about one file.
CHROME_SKIP_ASSETS = {"footer"}


CHROME_ORDER = ("nav", "footer")

STACK = (
    "Next.js 16 App Router, static export. React 19. TypeScript. Tailwind v4. "
    "Motion 13 from 'motion/react'. Icons from 'lucide-react'. "
    "next/image with `unoptimized` (static export)."
)


def _bb(run: Run) -> Blackboard:
    return Blackboard.model_validate_json(run.blackboard_path.read_text())


# --------------------------------------------------------------- one write path
#
# CLAUDE.md §3: agents propose diffs, an orchestrator applies or rejects them,
# and every state transition is recorded so a run is replayable. `Store.apply` is
# that mechanism and until now these step functions went around it — `_save` did
# `bb.version += 1` and dumped the whole model over the file. Measured across the
# six exported projects, that is exactly what the blackboard shows: `version`
# climbing (brief, sources, design all went through `_save`) and `decisions`
# empty on every one, because the decision log only ever gets written by the path
# nothing was using.
#
# Everything below routes through `Store.apply`. That buys three things `_save`
# could not: the patch is validated against the schema before it lands, the write
# is atomic (see `Store._write`), and each transition leaves a Decision naming
# the agent that caused it.
#
# A rejection is NOT raised. Persistence must never change what a run produces —
# a build that succeeded and then failed to record itself is still a build that
# succeeded, and turning a bookkeeping failure into a dead stage would be a worse
# bug than the one this fixes. Callers surface the rejection as a `blocked` event
# and carry on.


# The prefix that identifies an adoption in the decision log, so a later
# adoption can name the one it supersedes without re-deriving what "adopted"
# looks like in two places.
_ADOPTED = "direction adopted: #"


def _store(run: Run) -> Store:
    return Store(run.blackboard_path)


def telemetry_note(run: Run, where: str, rejected: Rejected) -> None:
    """Where a rejection cannot become an Event, it still has to become a line.

    `adopt_direction` and `record_asset_decisions` are called from the HTTP layer,
    not from inside a stage generator, so there is nothing to yield into. A
    rejection swallowed here is a decision that silently did not get logged,
    which is the exact class of bug this work exists to close.
    """
    from sparrow import telemetry

    telemetry.log_stage("blackboard", "blocked",
                        f"{where}: {rejected.code} — {rejected.message}")


def _note(run: Run, *, agent: str, summary: str,
          supersedes: str | None = None) -> Rejected | None:
    """Record a decision that changes no other field.

    An empty patch is deliberate: the decision IS the state change. A Fixer
    dispute moves nothing on the blackboard and is precisely the thing that was
    unrecoverable afterwards — one run burned three rounds and ~$2 on four
    disputes whose text existed only in a `disputed` dict that died with the
    process.
    """
    r = _store(run).apply([], agent=agent, summary=_safe(summary),
                          supersedes=supersedes)
    return r if isinstance(r, Rejected) else None


# Decisions are read back by agents, rendered into prompts and copied into logs.
# `Asset.scrubbed` already carries the rule for the same reason: record the shape
# of a thing, never the value. Nothing here composes user text into a summary —
# the summaries are section ids, status names, defect codes and agent-authored
# prose about code — and the cap keeps a runaway model reply from turning the
# decision log into the biggest field on the blackboard.
_SUMMARY_MAX = 400


def _safe(summary: str) -> str:
    one_line = " ".join(summary.split())
    return one_line if len(one_line) <= _SUMMARY_MAX else one_line[:_SUMMARY_MAX - 1] + "…"


def _replace(run: Run, path: str, value, *, agent: str, summary: str,
             supersedes: str | None = None) -> Rejected | None:
    """Replace one top-level field. The shape every old `_save` call really had."""
    r = _store(run).apply([{"op": "replace", "path": path, "value": value}],
                          agent=agent, summary=_safe(summary), supersedes=supersedes)
    return r if isinstance(r, Rejected) else None


def _record_section(run: Run, section_id: str, *, agent: str,
                    status: BuildStatus | None = None,
                    bump_attempt: bool = False,
                    defects: list[str] | None = None,
                    note: str = "") -> Rejected | None:
    """Move one section's build state, immediately, as it moves.

    Per section rather than per stage. `step_build` used to write nothing at all
    until the stage ended, so a run that died on section six left nine sections
    reading `pending / 0 attempts` — an accurate record of a build that never
    happened, on a project with six built files on disk. That record is what
    resume reads, so it has to be true at every instant, not only at the end.

    The index is resolved against a FRESH read rather than against the caller's
    in-memory blackboard: by the time a build reaches section six the caller's
    copy is five versions stale, and an index taken from it points at whatever
    happens to sit there now.
    """
    bb = _bb(run)
    idx = next((i for i, s in enumerate(bb.sections) if s.id == section_id), None)
    if idx is None:
        return Rejected("unknown-section",
                        f"no section {section_id!r} on this blackboard")
    current = bb.sections[idx]

    patch: list[dict] = []
    parts: list[str] = []
    if status is not None and status is not current.status:
        patch.append({"op": "replace", "path": f"/sections/{idx}/status",
                      "value": status.value})
        parts.append(f"{current.status.value} → {status.value}")
    if bump_attempt:
        patch.append({"op": "replace", "path": f"/sections/{idx}/attempts",
                      "value": current.attempts + 1})
        parts.append(f"attempt {current.attempts + 1}")
    if defects is not None and defects != current.defects:
        patch.append({"op": "replace", "path": f"/sections/{idx}/defects",
                      "value": [_safe(d) for d in defects]})
        parts.append(f"{len(defects)} defect(s)" if defects else "defects cleared")

    if not patch and not note:
        return None                      # nothing moved; do not bump the version
    summary = f"{section_id}: " + " · ".join([*parts, *( [note] if note else [] )])
    r = _store(run).apply(patch, agent=agent, summary=_safe(summary))
    return r if isinstance(r, Rejected) else None


def reset_sections(run: Run, section_ids: list[str]) -> list[str]:
    """Send named sections back to PENDING so a re-advance rebuilds only those.

    The user-facing half of resume: "just redo the hero". Without it, persisted
    state means a resumed run skips every built section forever and there is no
    way to ask for one of them again.

    Raises ValueError on an unknown id rather than silently resetting nothing —
    a typo that reports success and rebuilds nothing is the failure this is
    for.
    """
    bb = _bb(run)
    known = {s.id for s in bb.sections}
    unknown = sorted(set(section_ids) - known)
    if unknown:
        raise ValueError(f"no such section(s): {', '.join(unknown)}")
    done = []
    for sid in section_ids:
        _record_section(run, sid, agent="orchestrator", status=BuildStatus.PENDING,
                        defects=[], note="reset for rebuild at the user's request")
        done.append(sid)
    return done


# ------------------------------------------------------------------ gate 1

def step_brief(run: Run) -> Iterator[Event]:
    """The brief has to be complete before anything is generated — including the
    name.

    Measured across all eight real projects: `product_name` was `""` on every
    single one. The interviewer asks for it (INTERVIEW_SYSTEM) and correctly
    refuses to invent one when the user did not say, and then nothing followed
    up — so the run carried on and every downstream agent read the "not given"
    branch of `context_block`. The result is a site with no identity: a lucide
    phone icon labelled "Platform home" where the wordmark goes, a page title
    made of the offering sentence truncated mid-word, and a generated hero
    screenshot advertising a company called "Off-Hook" that appears nowhere
    else on the page.

    This asks at GATE 1 rather than adding a gate. §8's rule is that gates are
    few; the name is part of "what are we building", which is the question gate
    1 already exists to ask. It is only reached when the interviewer could not
    extract one, so a prompt that named the product never sees this stop.
    """
    bb = _bb(run)
    if bb.brief is None:
        raise Halt(GateRequest(
            Stage.GATE_BRIEF,
            "What are we building, and who is it for?",
            options=[], artifacts=[],
        ))
    if not bb.brief.product_name.strip():
        raise Halt(GateRequest(
            Stage.GATE_BRIEF,
            "What is it called? The name goes in the navigation, the footer, "
            "the browser tab, the copy and the product screenshots, and nothing "
            "downstream is allowed to make one up.",
            options=[{
                "kind": "product_name",
                "question": "What is the product or business called?",
                "why": "Every section has to agree on it. Without it the nav "
                       "shows an icon instead of your name and a generated "
                       "screenshot invents a brand of its own.",
                "choices": [{"choice": "name",
                             "label": "Type the name, exactly as you write it",
                             "field": "product_name"}],
            }],
            artifacts=[],
        ))
    yield Event(Stage.BRIEF, "progress",
                f"{bb.brief.product_name} · {bb.brief.category} · "
                f"{len(bb.active_constraints())} constraint(s)")


def record_product_name(run: Run, name: str) -> str:
    """Settle the name on the blackboard. Raises ValueError on an empty answer.

    Refused rather than defaulted. A blank here would put the run straight back
    into the "not given" branch every one of the eight measured projects took,
    and the point of the gate is that it is the one place the name can be
    settled by the only party who knows it.
    """
    if _bb(run).brief is None:
        raise ValueError("there is no brief yet — gate 1 is asking for the whole "
                         "brief, not only the name")
    name = " ".join(name.split())
    if not name:
        raise ValueError(
            "the name cannot be blank — it is printed in the nav, the footer, "
            "the browser tab and inside every generated product screenshot, and "
            "no agent is allowed to invent one")
    rejected = _replace(run, "/brief/product_name", name,
                        agent="user@gate:brief",
                        summary=f"product name settled: {name}")
    if rejected:
        telemetry_note(run, "record_product_name", rejected)
        raise ValueError(f"name not recorded ({rejected.code}): {rejected.message}")
    return name


# ------------------------------------------------------------------ sources

def step_sources(run: Run, urls: list[str]) -> Iterator[Event]:
    from sparrow.agents.blueprinter import Blueprinter, to_markdown
    from sparrow.providers import Tier, get_provider
    from sparrow.rank import (RANKABLE, Candidate, commonality, pick_primary,
                             primary_order,
                              rank_section, to_design_brief)
    from sparrow.scout import classify, extract

    bb = _bb(run)
    provider = get_provider()
    labelled: dict[str, list[tuple[str, int]]] = {}
    extracts: dict[str, object] = {}
    by_type: dict[str, list[Candidate]] = {}
    by_type_all: dict[str, list[Candidate]] = {}   # includes chrome, for blueprints
    registers: dict[str, object] = {}
    vocabulary: dict[str, object] = {}   # counted components, per source
    out_dir = run.dir / "sources"

    for url in urls:
        site = url.split("//")[-1].split("/")[0]
        # shots=True. This defaulted to True and the sources stage turned it
        # off, so no agent in the pipeline had ever seen a source site — the
        # design agent designed from a word count and the builder built from
        # prose. A section screenshot is ~1,700 tokens against a $3.50 run.
        r = extract(url, out_dir, shots=True)
        if not r.ok or len(r.bands) < 4:
            yield Event(Stage.SOURCES, "blocked",
                        f"{site}: unreadable or too thin — skipped")
            continue
        if r.register is not None:
            registers[site] = r.register
            extracts[site] = r
            # The register report is computed from registers alone; enclosure is
            # summed over bands, so hand it the bands.
            r.register._bands = r.bands
        # On the Register, not on the extract. Reading `r.components` raised
        # AttributeError and killed the whole sources stage on a live run — the
        # unit test for this passed because it handed the blueprinter a dict
        # directly and never exercised this seam.
        if r.register is not None and r.register.components is not None:
            vocabulary[site] = r.register.components
        types = classify(provider, r.bands)
        labelled[site] = [(t, b.index + 1) for t, b in zip(types, r.bands)]
        for t, b in zip(types, r.bands):
            cand = Candidate(site, t, b.index + 1, b.height, b.words, b.images,
                             b.buttons, b.listItems, b.headings, b.text, b.unrendered,
                             shot=b.shot, html=b.html,
                             content_share=getattr(b, "contentShare", 0.0) or 0.0,
                             inset=getattr(b, "inset", 0) or 0,
                             pad_top=getattr(b, "padTop", 0) or 0,
                             pad_bot=getattr(b, "padBot", 0) or 0,
                             enclosure=dict(getattr(b, "enclosure", None) or {}),
                             ground=dict(getattr(b, "ground", None) or {}),
                             proof=dict(getattr(b, "proof", None) or {}),
                             density=dict(getattr(b, "density", None) or {}))
            by_type_all.setdefault(t, []).append(cand)
            if t in RANKABLE:
                by_type.setdefault(t, []).append(cand)
        yield Event(Stage.SOURCES, "progress", f"{site}: {len(r.bands)} sections")

    if len(labelled) < 2:
        raise RuntimeError("need at least two readable sources to rank")

    # Keep the measured palettes so the design gate can show them without refetching.
    from dataclasses import asdict
    pals = {s: asdict(r.palette) for s, r in registers.items()
            if getattr(r, "palette", None)}
    if pals:
        (out_dir / "palettes.json").write_text(json.dumps(pals, indent=2))

    # WHAT THE SOURCES DO WITH VIDEO, KEPT. `registers` is built here, used to
    # phrase one line for the blueprinter, and then dropped when this stage
    # returns — so the pass that decides which section carries motion, two
    # stages later, could not see it at all. Nothing downstream could allocate
    # a video because nothing downstream knew there was any.
    vids = [dict(v, site=s) for s, r in registers.items()
            for v in (getattr(r, "videos", None) or [])]
    if vids:
        (run.dir / MOTION).write_text(json.dumps(vids, indent=2))

    # And what they draw on canvas — the frames the scout now takes of the
    # particle fields, glows and generative textures a page keeps where markup
    # cannot express it. `canvas: 4` was all the design director ever got.
    surf = [dict(c, site=s) for s, r in registers.items()
            for c in (getattr(r, "canvases", None) or [])]
    if surf:
        (run.dir / SURFACES).write_text(json.dumps(surf, indent=2))

    # And the type each source is set in — measured, so any later stage can
    # read the register the sources share instead of guessing at it.
    typo = {s: r.typography for s, r in registers.items()
            if getattr(r, "typography", None)}
    if typo:
        (run.dir / "typography.json").write_text(json.dumps(typo, indent=2))

    # And how each source separates its content, summed over its bands — the
    # measurement that decides whether a page is built from boxes or from
    # space, and until now the one the design agent never had.
    enc: dict[str, dict] = {}
    for site, r in extracts.items():
        tot = {"blocks": 0, "bordered": 0, "shadowed": 0, "filled": 0, "rounded": 0, "rules": 0}
        for b in r.bands:
            e = getattr(b, "enclosure", None) or {}
            for k in tot:
                tot[k] += int(e.get(k, 0) or 0)
        if tot["blocks"]:
            enc[site] = dict(tot, enclosed=round((tot["bordered"] + tot["shadowed"]) / tot["blocks"], 3),
                             filled_share=round(tot["filled"] / tot["blocks"], 3))
    if enc:
        (run.dir / "enclosure.json").write_text(json.dumps(enc, indent=2))

    # The GROUND MAP: every band of every source, in order, with what it sits
    # on. The register counts "2 grounds, 3 changes"; the winners carry only
    # the bands that won a section. Neither says WHERE down the page a source
    # drops into a dark band or puts its copy on a picture, and where is the
    # rhythm. The composer reads this beside the page sheet.
    grounds: dict[str, list[dict]] = {}
    for site, r in extracts.items():
        rows = []
        for b in r.bands:
            g = getattr(b, "ground", None) or {}
            if not g:
                continue
            rows.append({"band": b.index, "top": b.top, "height": b.height,
                         "hex": g.get("hex"), "lum": g.get("lum"),
                         "differs": bool(g.get("differs")), "layered": bool(g.get("layered")),
                         "heading": (b.headings or [""])[0][:60]})
        if rows:
            grounds[site] = rows
    if grounds:
        (run.dir / GROUNDS).write_text(json.dumps(grounds, indent=2))

    # DENSITY by section type across every source, so the audit can hold a
    # built section to the range the sources actually span for that type
    # rather than to one band or to a number of mine. `labelled` is the
    # classifier's (type, position) per site; the bands are indexed 0-based.
    dens: dict[str, list[dict]] = {}
    for site, r in extracts.items():
        by_pos = {b.index + 1: b for b in r.bands}
        for t, pos in labelled.get(site, []):
            b = by_pos.get(pos)
            d = getattr(b, "density", None) if b is not None else None
            if d:
                dens.setdefault(t, []).append({"site": site, "band": pos, **d})
    if dens:
        (run.dir / DENSITY).write_text(json.dumps(dens, indent=2))

    comm = commonality(labelled)
    primary, why, usage = pick_primary(provider, bb.brief, labelled)
    yield Event(Stage.SOURCES, "progress", f"primary reference: {primary}",
                cost=usage.cost(provider.name, Tier.CHEAP))

    rankings: dict[str, dict] = {}
    for t in comm.typical_order:
        if not by_type.get(t):
            continue
        r, u = rank_section(provider, bb.brief, t, by_type[t])
        rankings[t] = r
        if u is not None:
            run.spent += u.cost(provider.name, Tier.CHEAP)

    _brief_md = to_design_brief(comm, primary, why, rankings, registers)
    # Written down because `build` is a separate stage in a separate process and
    # the per-section winners do not imply it: on fernbank they split brex 5 /
    # ramp 3 / mercury 1 while the primary — the page whose ORDER AND PACING the
    # site takes, per the design brief — was ramp. Anything reading pacing off
    # "whichever site won the most sections" reads it off the wrong page.
    (out_dir / "primary.txt").write_text(primary)

    # One reading of the primary, by a model that can see it. Everything else
    # this stage produces is a count, and counts are what every agent after the
    # design director has ever had. Stored as an artifact rather than passed as
    # a message (§3), so the composer, the blueprinter and the builder read the
    # same reading rather than each re-deriving one from a single band.
    from sparrow.agents.reader import Reader

    reading: dict = {}
    try:
        rdr = Reader(provider)
        obs, portrait, u = rdr.read(
            bb, site=primary,
            images=[x for x in (_page_sheet(run), *_winner_shots(run, 5)) if x],
            counted=comm.report())
        run.spent += u.cost(provider.name, rdr.tier)
        reading = {"site": primary, "observations": obs, "portrait": portrait}
        (run.dir / READING).write_text(json.dumps(reading, indent=2))
        from sparrow.agents.reader import to_block
        _brief_md = _brief_md + "\n\n" + to_block(reading)
        yield Event(Stage.SOURCES, "progress",
                    f"read {primary}: {len(obs)} observation(s)"
                    + (f" · {portrait[:60]}" if portrait else ""))
    except Exception as e:
        # Never fatal. A source the reader cannot parse is a source the harness
        # still has counts for, and a stage that dies here would take the
        # blueprints and the sitemap with it.
        yield Event(Stage.SOURCES, "blocked",
                    f"could not read {primary} ({type(e).__name__}) — "
                    "carrying on with the counted facts alone")

    # The winner's own screenshot and markup, per section type, kept for the
    # stages that run later. `sources` and `build` are separate stages in
    # separate processes, so evidence that is not written down here is evidence
    # the builder cannot have — which is exactly how it ended up building from
    # prose about a layout instead of the layout.
    winners: dict[str, dict] = {}
    for t, r in rankings.items():
        won = next((c for c in by_type.get(t, []) if c.site == r.get("winner")), None)
        if won is None:
            continue
        # WIDTH COMES FROM THE PRIMARY, not from whichever source won this
        # section. §5 gives the primary the rhythm and pacing, and width rhythm
        # is pacing. Measured on this run: vapi.ai alone spans 0.64 to 1.00 with
        # two full-bleed bands, but taking each section's width from its own
        # winner across three sources collapsed the page to 0.68-0.86 and lost
        # both extremes — the same averaging `typical_order` used to do to
        # section order, one level down. The winner still supplies the shot, the
        # markup and the arrangement; only the width follows the primary.
        own = next((c for c in by_type_all.get(t, []) if c.site == primary), None)
        winners[t] = {"site": won.site,
                      "shot": str(won.shot) if won.shot else None,
                      "html": won.html,
                      "content_share": (own or won).content_share,
                      "inset": (own or won).inset,
                      "width_from": (own or won).site,
                      # The band's own weight, so the composer can see that the
                      # source's hero holds 29 words and no product image rather
                      # than only that it is 0.9 wide. Density is a decision the
                      # composer makes, and it made it blind: every hero came out
                      # carrying the busiest object on the page under a headline
                      # the sources leave alone.
                      "words": won.words, "images": won.images,
                      "buttons": won.buttons, "height": won.height,
                      "pad_top": won.pad_top, "pad_bot": won.pad_bot,
                      "enclosure": won.enclosure, "ground": won.ground,
                      "proof": won.proof, "density": won.density}
    for name in CHROME_ORDER:
        cands = by_type_all.get(name, [])
        if cands:
            own = next((c for c in cands if c.site == primary), None)
            winners[name] = {"site": cands[0].site,
                             "shot": str(cands[0].shot) if cands[0].shot else None,
                             "html": cands[0].html,
                             "content_share": (own or cands[0]).content_share,
                             "inset": (own or cands[0]).inset,
                             "width_from": (own or cands[0]).site,
                             "words": cands[0].words, "images": cands[0].images,
                             "buttons": cands[0].buttons, "height": cands[0].height,
                             "pad_top": cands[0].pad_top, "pad_bot": cands[0].pad_bot,
                             "enclosure": cands[0].enclosure, "ground": cands[0].ground,
                             "proof": cands[0].proof, "density": cands[0].density}
    (run.dir / WINNERS).write_text(json.dumps(winners, indent=2))

    (out_dir / "design-brief.md").write_text(_brief_md)

    bp_dir = run.dir / "blueprints"
    bp_dir.mkdir(parents=True, exist_ok=True)
    bper = Blueprinter(provider)
    # The primary's own sequence, not the mean of the sources — §5's skeleton.
    order = primary_order(labelled, primary, comm)

    # Measured, then never shown to the one agent that acts on it. rank.py puts
    # "large product images: N per page on average" in the design brief, which
    # the design director reads and the blueprinter does not — and the
    # blueprinter is what decides whether a section has any imagery at all.
    _imgs = [r.product_images for r in (registers or {}).values() if r]
    imagery = (
        f"These sources carry {sum(_imgs) / len(_imgs):.0f} large product images "
        f"per page on average, across {len(_imgs)} site(s). Per section that is "
        f"roughly {sum(_imgs) / len(_imgs) / max(1, len(order)):.1f}."
    ) if _imgs else ""

    # What the sources do with video, in the words the blueprinter needs to act
    # on: whether it is decoration or content, and what shape it is.
    _vids = [v for r in (registers or {}).values() for v in (getattr(r, "videos", None) or [])]
    if _vids:
        amb = [v for v in _vids if v.get("muted") and v.get("loop") and not v.get("controls")]
        bleed = [v for v in _vids if v.get("bleed")]
        w = sorted(v["w"] for v in _vids)[len(_vids) // 2]
        h = sorted(v["h"] for v in _vids)[len(_vids) // 2]
        motion_line = (
            f"These sources carry {len(_vids)} video(s). "
            + (f"{len(amb)} are muted looping autoplay — decoration with nothing to "
               "press. " if amb else "")
            + (f"{len(bleed)} run full-bleed behind a section. "
               if bleed else f"None are full-bleed; they sit in the layout at about "
               f"{w}x{h}. ")
            + "Ask for a [video] only if this section is the one that would carry it, "
              "and never for anything a reader must read."
        )
    else:
        motion_line = ""

    # Chrome gets blueprints too, written from whatever the sources showed even
    # though it was never ranked.
    for name in CHROME_ORDER:
        cands = by_type_all.get(name, [])
        stub = {"winner": cands[0].site if cands else None,
                "why": "page chrome — required on every page, not ranked",
                "adopt": [], "unopposed": True}
        bp, u = bper.write(bb.brief, name, stub, cands,
                           [x for x in order if x in rankings],
                           vocabulary=vocabulary,
                           shot=_b64(winners.get(name, {}).get("shot")),
                           imagery=imagery, motion=motion_line)
        comp = "".join(w.capitalize() for w in name.replace("-", " ").split())
        (bp_dir / f"{'00' if name == 'nav' else '99'}-{name}.md").write_text(
            to_markdown(bp, comp))
        run.spent += u.cost(provider.name, bper.tier)
        yield Event(Stage.SOURCES, "progress", f"chrome blueprint: {name}")

    for i, t in enumerate(order):
        if t not in rankings:
            continue
        bp, u = bper.write(bb.brief, t, rankings[t], by_type.get(t, []),
                           [x for x in order if x != t],
                           vocabulary=vocabulary,
                           shot=_b64(winners.get(t, {}).get("shot")),
                           imagery=imagery, motion=motion_line)
        comp = "".join(w.capitalize() for w in t.replace("-", " ").split())
        (bp_dir / f"{i + 1:02d}-{t}.md").write_text(to_markdown(bp, comp))
        run.spent += u.cost(provider.name, bper.tier)

    # Nav first, footer last, content between. Chrome is not ranked — every source
    # has both, so "which site does a footer best" is not a question — but it is
    # always built, because a page without navigation is not a page.
    from sparrow.rank import CHROME

    content = [t for t in order if t in rankings]
    sitemap = ["nav", *content, "footer"]
    bb.sections = [
        Section(id=t, order=i, blueprint_id=t,
                target_path=f"src/components/sections/"
                            f"{''.join(w.capitalize() for w in t.replace('-', ' ').split())}.tsx",
                component_name="".join(w.capitalize() for w in t.replace("-", " ").split()),
                # Every section on the page ground by default. Measured: wise,
                # stripe and linear all use ONE ground for the entire page and
                # never alternate. Forcing alternation banded our output into
                # nine visible blocks, which is most of what "it does not flow
                # like the sources" turned out to mean. If a design direction
                # wants a ground change it can ask for one; the default no
                # longer imposes it.
                ground=GROUND_PAGE)
        for i, t in enumerate(sitemap, 1)
    ]
    rejected = _replace(run, "/sections",
                        [s.model_dump(mode="json") for s in bb.sections],
                        agent="blueprinter",
                        summary=f"sitemap fixed: {len(bb.sections)} sections — "
                                + ", ".join(s.id for s in bb.sections))
    if rejected:
        yield Event(Stage.SOURCES, "blocked",
                    f"sitemap not recorded ({rejected.code}): {rejected.message}")
    yield Event(Stage.SOURCES, "done",
                f"{len(bb.sections)} sections · {len(rankings)} blueprints")


# ------------------------------------------------------------------ gate 2

def step_design(run: Run, alternatives: int = 3) -> Iterator[Event]:
    """Propose several directions, then stop. Re-rolling gives the same answer.

    Measured in experiments/variance-01: three runs on identical inputs produced
    byte-identical design systems. A gate whose "no" changes nothing is not a gate,
    so the options are generated up front and the human picks between them.
    """
    from sparrow.agents.design_director import DesignDirector

    bb = _bb(run)
    sources = (run.dir / "sources" / "design-brief.md").read_text()

    # If the last gate was answered "none of these", the note steers this pass.
    redirect = run.dir / "redirect.txt"
    if redirect.exists():
        sources += ("\n\n<the_user_rejected_the_previous_directions>\n"
                    f"They asked for: {redirect.read_text().strip()}\n"
                    "Take that seriously and literally. It is a correction to the "
                    "direction, not a nuance to blend in.\n"
                    "</the_user_rejected_the_previous_directions>")
        redirect.unlink()
        # The FACT of the re-roll, never the sentence they typed. The steer
        # itself is the user's own words about their own business and the
        # decision log is read into prompts and copied into logs; the design
        # system this produces is where that steer becomes visible and
        # inspectable. What is unrecoverable without this line is that these
        # three directions are a second set, not the first.
        rejected = _note(run, agent="design-director",
                         summary="previous directions rejected at gate 2 — "
                                 "re-proposing against the user's correction")
        if rejected:
            yield Event(Stage.DESIGN, "blocked",
                        f"re-roll not recorded ({rejected.code}): {rejected.message}")

    dd = DesignDirector()
    proposals, seen = [], []
    for i in range(alternatives):
        surf_txt = surface_facts(load_surfaces(run))
        ds, revised, u = dd.direct(
            bb,
            sources=sources + (f"\n\n<canvas_layer>\n{surf_txt}\n</canvas_layer>"
                               if surf_txt else ""),
            avoid=seen or None,
            shots=[x for x in
                   (_page_sheet(run), *_winner_shots(run), *surface_shots(run))
                   if x])
        seen.append(ds)
        proposals.append({"index": i, "signature": ds.signature,
                          "atmosphere": ds.atmosphere,
                          "type": f"{ds.font_display} / {ds.font_body}",
                          "revised": revised,
                          "design_system": ds.model_dump(mode="json")})
        yield Event(Stage.DESIGN, "progress", f"direction {i + 1}: {ds.signature[:64]}",
                    cost=u.cost(dd.provider.name, dd.tier))

    (run.dir / "directions.json").write_text(json.dumps(proposals, indent=2))

    # Render each direction, and what the sources are actually painted with.
    # This gate fixes every visual decision downstream, and it was being asked in
    # language only the design agent understands — "a perforated remittance-advice
    # ribbon carrying real currency pairs". §8 wants concrete options a business
    # owner can answer, and swatches are answerable where that sentence is not.
    from sparrow.specimen import direction_html, render, sources_html

    html = {f"direction-{i}": direction_html(seen[i], i) for i in range(len(seen))}
    pals = {s: r.palette for s, r in _source_palettes(run).items()}
    if pals:
        html["sources"] = sources_html(pals)
    for r in render(html, run.dir / "specimens"):
        yield Event(Stage.DESIGN, "progress", f"specimen: {r.name}")

    prefix = f"/projects/{run.project_id}/specimens"
    dark_count = sum(1 for p in pals.values() if p.dark)
    raise Halt(GateRequest(
        Stage.GATE_DESIGN,
        "Which direction should the site take?"
        + (f"  ({dark_count} of {len(pals)} of your reference sites use a dark ground.)"
           if pals else ""),
        options=[
            *[{**{k: p[k] for k in ("index", "signature", "atmosphere", "type")},
               "specimen": f"{prefix}/direction-{p['index']}.png"}
              for p in proposals],
            {"index": -1, "choice": "other",
             "signature": "None of these — describe what you want instead",
             "atmosphere": "Say what to change (darker, warmer, bolder, less green) "
                           "and three new directions are proposed against it.",
             "type": "", "specimen": None},
        ],
        artifacts=[str(run.dir / "specimens"),
                   *( [f"{prefix}/sources.png"] if pals else [] )],
    ))


def _source_palettes(run: Run) -> dict:
    """Re-read the palettes captured during SOURCES, without re-fetching."""
    p = run.dir / "sources" / "palettes.json"
    if not p.exists():
        return {}
    from sparrow.scout import Palette

    return {site: type("R", (), {"palette": Palette(**d)})()
            for site, d in json.loads(p.read_text()).items()}


def adopt_direction(run: Run, index: int) -> None:
    """Write the chosen direction onto the blackboard AND into the workspace.

    Writing it to the blackboard alone is what the first real run did, and the
    design system then never reached the files: no tokens in globals.css, no font
    families bound in layout.tsx. Adopting a direction has to mean both.
    """
    from sparrow.blackboard.schema import DesignSystem

    proposals = json.loads((run.dir / "directions.json").read_text())
    bb = _bb(run)
    chosen = DesignSystem.model_validate(proposals[index]["design_system"])

    # A re-roll ("none of these") replaces a direction that was already adopted,
    # and a replacement is not an addition — CLAUDE.md §4. The trace is the one
    # line that makes "why does this look different from what I approved"
    # answerable after the fact, so the superseded decision is named rather than
    # left to be inferred from two adoptions in a row.
    previous = next((d.id for d in reversed(bb.decisions)
                     if d.summary.startswith(_ADOPTED)), None)
    bb.design_system = chosen
    rejected = _replace(run, "/design_system", chosen.model_dump(mode="json"),
                        agent="design-director",
                        summary=f"{_ADOPTED}{index} — {chosen.signature}",
                        supersedes=previous)
    if rejected:                       # recorded or not, the direction is adopted
        telemetry_note(run, "adopt_direction", rejected)
    apply_design_system(run, bb)


def apply_design_system(run: Run, bb: Blackboard) -> None:
    """Render the design system into globals.css and bind its fonts in layout.tsx."""
    from sparrow.render.tokens import apply_to_stylesheet, font_imports

    ws = run.workspace
    css_path = ws / "src/app/globals.css"
    css_path.write_text(apply_to_stylesheet(css_path.read_text(), bb.design_system))

    imp, consts, rest = font_imports(bb.design_system, run.workspace)
    cls, theme = rest.split("|||")
    layout = ws / "src/app/layout.tsx"
    src = layout.read_text()
    src = re.sub(r'import \{[^}]*\} from "next/font/google";\n', "", src)
    src = re.sub(r"const \w+ = \w+\(\s*\{\s*subsets.*?\}\s*\);\n", "", src, flags=re.S)
    src = src.replace('import "./globals.css";', f'import "./globals.css";\n{imp}\n{consts}')
    src = re.sub(r"\s*// Font families are bound[^\n]*\n", "\n    ", src)
    src = re.sub(r'<html lang="en"[^>]*>',
                 f'<html lang="en" className={{cn("font-body", `{cls}`)}}>', src)
    if "@/lib/utils" not in src:
        src = src.replace('import "./globals.css";',
                          'import "./globals.css";\nimport { cn } from "@/lib/utils";')
    layout.write_text(src)

    css = css_path.read_text()
    css = re.sub(r"\n *--font-(display|body|mono|weight-\d+): [^;]+;", "", css)
    css_path.write_text(css.replace("@theme inline {", f"@theme inline {{\n{theme}"))


# ------------------------------------------------------------------ build

# ------------------------------------------------------------- the asset gate

CONTENT_FILE = "content.json"


def load_content(run: Run) -> dict:
    f = run.dir / CONTENT_FILE
    return json.loads(f.read_text()) if f.exists() else {}


def save_content(run: Run, content: dict) -> None:
    (run.dir / CONTENT_FILE).write_text(json.dumps(content, indent=2))


def composition_block(bb, section, source_band: dict | None = None) -> str:
    """What shape this section is, what surrounds it, and what it may use.

    The neighbours are named on purpose. "You are full-bleed" is followed
    without understanding; "you are full-bleed and the section above you is a
    contained band on muted" is the difference the reader actually sees, and it
    is the only way a builder that cannot see its neighbours can avoid matching
    them by accident.

    Treatments and the signature are ALLOCATION, and they are stated as limits
    rather than options. Given the whole list and asked to pick, the last build
    put a gradient in six sections of ten and repeated the signature motif down
    the page — busy for the same reason ten identical containers were flat.
    """
    order = sorted(bb.sections, key=lambda x: x.order)
    i = next((n for n, x in enumerate(order) if x.id == section.id), None)
    if i is None or not section.archetype:
        return ""

    def line(x) -> str:
        w = f"{x.content_share:.2f} of the viewport" if x.content_share else x.width.value
        return f"{x.id}: {w}, {x.ground} ground, {x.archetype}"

    parts = [
        "<composition>",
        "The shape of this section was decided for the whole page at once, by the "
        "agent that could see all of it. It is not a suggestion and not yours to "
        "revise — the page's rhythm is the difference between these shapes.",
        "",
        f"  YOUR SECTION — {line(section)}",
        # The name told the builder nothing it did not already assume. This is
        # the half that changes the output: classes, sides and ratios, quoted
        # from the pass that could see the whole page.
        *([f"  BUILD IT LIKE THIS — {section.archetype_how}",
           "  That is the skeleton, not a suggestion. If it puts the media left, the "
           "media goes left."] if section.archetype_how else []),
        *([f"  BUILD THE INSIDE LIKE THIS — {section.interior_how}",
           "  That is read off the source band's own markup: how many columns, what one "
           "item is made of, what separates items. Where it says no border, there is no "
           "border; where it says a rule, draw a rule."] if section.interior_how else []),
        f"  above you — {line(order[i - 1])}" if i > 0 else "  you open the page",
        f"  below you — {line(order[i + 1])}" if i + 1 < len(order) else "  you close the page",
        "",
        f"  what must make yours different: {section.contrast}",
        "",
    ]
    if section.carries_signature:
        parts += [
            "  YOU CARRY THE SIGNATURE. This is the one section on the page that states",
            "  the design system's signature element at full strength. Build it as the",
            "  thing this page is remembered for.",
        ]
    else:
        parts += [
            "  You do NOT carry the signature. Another section states it at full",
            "  strength; restating it here turns the page's one memorable element into",
            "  a repeated motif. Reference it faintly, or not at all.",
        ]
    parts.append("")
    if section.treatments:
        parts += [
            "  YOUR TREATMENTS, by name: " + ", ".join(section.treatments) + ".",
            "  Apply these and no others. A treatment not named here belongs to a",
            "  different section; using it anyway is how a page ends up with the same",
            "  gradient in six places.",
        ]
    else:
        parts += [
            "  NO TREATMENTS are allocated to this section. Build it from the ground,",
            "  the type and the layout. That is a deliberate choice, not an omission —",
            "  a page where every section is treated has no quiet left in it.",
        ]
    parts += [
        "",
        (f"  YOUR CONTENT SPANS {section.content_share:.2f} OF THE VIEWPORT — "
         f"about {round(section.content_share * 1440)}px at 1440. That is measured "
         "off the source section this one is built from, not chosen from a list. "
         "Set a max-width that lands there and inset the rest; at 1.00 the content "
         "runs edge to edge with no side gutter."
         if section.content_share else
         "  contained — the standard max-width column, centred.\n"
         "  wide — wider than the column, still inset from the viewport edge.\n"
         "  full-bleed — edge to edge, no side gutter on the outer element."),
        "  page ground — `bg-background`.  muted ground — `bg-muted`.",
        *([f"  YOUR GROUND `{section.ground}` IS PAINTED BY — {section.ground_how}",
           "  Those classes go on the section root; the copy sits on that ground, so ",
           "  set text colour to read against it."] if section.ground_how else []),
    ]
    # HOW THE SOURCE BAND SEPARATES ITS CONTENT — measured, per section, from the
    # same winners record the width line above is read from. Every page built
    # here put its content in `rounded-lg border border-border bg-card` boxes,
    # nine to a section, against sources that box 7-17% of their blocks; the
    # builder had the source's width to the pixel and nothing at all about
    # whether that source drew edges around things. The number is the source's
    # own: a source that boxes 40% of its blocks reads that way here and the
    # builder boxes. A source that boxes none reads that way too.
    d = (source_band or {}).get("density") or {}
    if d.get("words_per_k"):
        parts.append(
            f"  DENSITY, measured off the source band: {d['words_per_k']} words and "
            f"{d.get('elements_per_k', '?')} elements per 1000px of height. Height is a "
            "consequence of content, not a target: a band carrying half the words over "
            "the same height reads as unfinished.")
    e = (source_band or {}).get("enclosure") or {}
    n = int(e.get("blocks") or 0)
    if n:
        boxed = int(e.get("bordered") or 0) + int(e.get("shadowed") or 0)
        sep = ("hairline rules" if e.get("rules") and not e.get("filled") else
               "changes of ground colour" if e.get("filled") else "whitespace alone")
        if boxed == 0:
            parts.append(
                f"  ENCLOSURE, measured off the source band: 0 of {n} blocks are boxed; "
                f"content is separated by {sep}.")
        else:
            parts.append(
                f"  ENCLOSURE, measured off the source band: {boxed} of {n} blocks are "
                f"boxed ({e.get('bordered', 0)} bordered all round, {e.get('shadowed', 0)} "
                f"shadowed); the rest are separated by {sep}.")
    parts.append("</composition>")
    return "\n".join(parts)


def step_compose(run: Run) -> Iterator[Event]:
    """Decide the shape of every section, once, seeing the whole page.

    Runs after a direction is adopted and before anything is built. It exists
    because §6's "the design agent's recorded decisions are what the builder is
    held to" covered palette, type and spacing but never covered SHAPE — and the
    builder's own prompt tells it "you do NOT see any other section" while also
    telling it composition is its own. Both cannot hold: rhythm is a property
    between sections, so ten agents deciding shape alone all pick the median and
    the page comes out as ten identical bands. Measured on fernbank2: ten
    sections, one ground, one width, one archetype.

    Idempotent. A section already carrying an archetype keeps it, so a rerun
    after a rebuild does not re-decide a page that is half built.
    """
    from sparrow.agents.design_director import DesignDirector
    from sparrow.blackboard.schema import Width

    bb = _bb(run)
    if bb.design_system is None or not bb.sections:
        return
    if all(s.archetype for s in bb.sections):
        yield Event(Stage.COMPOSE, "progress", "composition already decided — kept")
        return

    from sparrow.agents.reader import to_block

    winners_for_share = load_winners(run)
    dd = DesignDirector()
    # What each section's SOURCE band weighs. The composer decides density and
    # it decided blind: it knew the source hero was 0.9 wide, not that it held
    # 29 words, two buttons and no image. Evidence, in the same block as the
    # rest of what it sees about the page it is reproducing.
    wf = load_winners(run)
    def _vertical(w: dict) -> str:
        pt, pb, h = w.get("pad_top", 0), w.get("pad_bot", 0), w.get("height", 0)
        if not h or (pt + pb) < h * 0.15:
            return ""
        # Stated as the measurement, not a verdict. "HIGH" / "LOW" needed a
        # ratio and a pixel floor that were mine; the split itself is the
        # source's and the composer can read a ratio.
        return f"; content sits {pt}px from the top and {pb}px from the bottom of a {h}px band"

    def _boxes(w: dict) -> str:
        e = w.get("enclosure") or {}
        n = e.get("blocks") or 0
        if not n:
            return ""
        boxed = (e.get("bordered", 0) + e.get("shadowed", 0))
        if boxed == 0:
            sep = ("rules" if e.get("rules") else "ground changes" if e.get("filled") else "whitespace")
            return f"; NO boxes — {n} blocks separated by {sep}"
        return f"; {boxed} of {n} blocks boxed ({e.get('bordered',0)} bordered, {e.get('shadowed',0)} shadowed)"

    def _density(w: dict) -> str:
        d = w.get("density") or {}
        if not d.get("words_per_k"):
            return ""
        return f"; {d['words_per_k']} words and {d.get('elements_per_k', '?')} elements per 1000px"

    def _ground(w: dict) -> str:
        g = w.get("ground") or {}
        if not g:
            return ""
        lum = g.get("lum", 1.0)
        if g.get("layered"):
            return ("; sits on a PICTURE — a canvas, video, image or gradient covers "
                    f"most of the band (ground {g.get('hex')}, luminance {lum})")
        if g.get("differs"):
            return (f"; sits on ITS OWN GROUND {g.get('hex')} (luminance {lum}), "
                    f"not the page's {g.get('page')}")
        return ""

    weights = "\n".join(
        f"  {sid}: {w.get('words', '?')} words, {w.get('images', '?')} image(s), "
        f"{w.get('buttons', '?')} button(s), {w.get('height', '?')}px tall"
        f"{_vertical(w)}{_boxes(w)}{_density(w)}{_ground(w)} ({w.get('site')})"
        for sid, w in wf.items() if "words" in w)
    band_facts = (f"<source_bands>\nWhat each section's winning source band actually "
                  f"holds — its weight, not its width:\n{weights}\n</source_bands>"
                  if weights else "")
    motion_shots = [b for b in (_b64(v.get("frame")) for v in load_motion(run)
                                if v.get("frame") and v.get("w", 0) >= 240) if b][:3]
    ground_facts = ground_map(load_grounds(run))
    # The inside of each winning band, as structure. The composer decides the
    # skeleton from the screenshot; it decides the INTERIOR from this.
    skel = "\n".join(f"  {sid}: {_skeleton(w.get('html'))}"
                     for sid, w in wf.items() if w.get("html"))
    markup_facts = (f"<source_markup>\nEach winning source band's markup reduced to "
                    f"structure — tags, layout classes, `·12w` for twelve words of text, "
                    f"`<svg/>` for a mark. Read the interior off this: columns, what "
                    f"one item is made of, what separates items.\n{skel}\n</source_markup>"
                    if skel else "")
    plan, rhythm, usage = dd.compose(
        bb, shots=[x for x in (_page_sheet(run), *_winner_shots(run), *motion_shots) if x],
        observed=to_block(load_reading(run))
        + ("\n\n" + band_facts if band_facts else "")
        + ("\n\n" + ground_facts if ground_facts else "")
        + ("\n\n" + markup_facts if markup_facts else ""),
        motion=motion_facts(load_motion(run)))
    run.spent += usage.cost(dd.provider.name, dd.tier)

    applied = 0
    for section in sorted(bb.sections, key=lambda s: s.order):
        spec = plan.get(section.id) or {}
        # {name, how}, the bare word still accepted. "Two muted bands in a row
        # merge" used to be enforced here by flipping the second to page; that
        # was a rule written for sections that chose blind, and this pass sees
        # the whole page and the source's own ground changes — it can decide.
        g = spec.get("ground")
        if isinstance(g, dict):
            section.ground = " ".join(str(g.get("name", "page")).split()).lower()[:40] or GROUND_PAGE
            section.ground_how = " ".join(str(g.get("how", "")).split())[:300]
        else:
            section.ground = " ".join(str(g or "page").split()).lower()[:40]
            section.ground_how = ""
        if section.ground in ("page", "muted"):
            section.ground_how = ""
        elif not section.ground_how:
            # A name with no classes is the archetype failure over again — a
            # word the builder's prior beats. Without a `how` it is the page.
            section.ground = GROUND_PAGE
        try:
            width = Width(str(spec.get("width", "contained")).strip().lower())
        except ValueError:
            width = Width.CONTAINED
        section.width = width
        # {name, how}, with the bare string still accepted so a project composed
        # before `how` existed does not lose its archetype on a rerun.
        arch = spec.get("archetype")
        if isinstance(arch, dict):
            section.archetype = " ".join(str(arch.get("name", "")).split())[:60]
            section.archetype_how = " ".join(str(arch.get("how", "")).split())[:400]
        else:
            section.archetype = " ".join(str(arch or "").split())[:60]
            section.archetype_how = ""
        section.contrast = " ".join(str(spec.get("contrast", "")).split())[:200]
        inter = spec.get("interior")
        section.interior_how = " ".join(str(
            inter.get("how", "") if isinstance(inter, dict) else inter or "").split())[:500]
        known = {t.name for t in (bb.design_system.treatments or [])}
        section.treatments = [str(t) for t in (spec.get("treatments") or [])
                              if str(t) in known]
        # The source's own number, not the composer's word. The composer still
        # picks a width so a section with no matching source still has one, but
        # where the section was built from a real band, that band's measurement
        # wins — it is evidence and the word is a bucket.
        section.content_share = float(
            (winners_for_share.get(section.id) or {}).get("content_share") or 0.0)
        section.carries_signature = bool(spec.get("signature"))
        mo = spec.get("motion")
        if isinstance(mo, dict):
            section.carries_motion = bool(mo.get("carries"))
            section.motion_role = " ".join(str(mo.get("role", "")).split())[:160]
            pr = str(mo.get("prominence", "")).strip().lower()
            section.motion_prominence = pr if pr in ("dominant", "supporting", "thumbnail") else ""
        else:
            section.carries_motion = bool(mo)
            section.motion_role = ""
            section.motion_prominence = ""
        applied += 1

    # Exactly one owner. The rule is "spend your boldness in one place", so a
    # composer that marks three sections has not allocated the signature, it has
    # spread it — and a composer that marks none leaves the page with no focal
    # section at all. Settled here rather than asked for again.
    owners = [x for x in bb.sections if x.carries_signature]
    if len(owners) != 1:
        for x in bb.sections:
            x.carries_signature = False
        focal = (owners[0] if owners else
                 next((x for x in sorted(bb.sections, key=lambda y: y.order)
                       if x.id == "hero"), None) or
                 sorted(bb.sections, key=lambda y: y.order)[0])
        focal.carries_signature = True

    # AT MOST ONE, AND ONLY IF THE SOURCES ACTUALLY USE VIDEO. Same clamp as the
    # signature above and for the same reason: a composer that marks four
    # sections has not allocated the motion, it has scattered it. The difference
    # from `signature` is the floor — a page with no video is a correct outcome
    # when the sources have none, so this never promotes one.
    movers = [x for x in bb.sections if x.carries_motion]
    if not load_motion(run):
        for x in movers:
            x.carries_motion = False
    elif len(movers) > 1:
        keep = min(movers, key=lambda x: x.order)
        for x in movers:
            x.carries_motion = x is keep
    for x in bb.sections:
        if not x.carries_motion:
            x.motion_role = ""
            x.motion_prominence = ""

    # Through Store.apply like every other transition, so the composition leaves
    # a Decision naming the agent that made it — §3's replayability is the whole
    # reason the sections carry these fields instead of a sidecar file.
    rejected = _replace(run, "/sections",
                        [x.model_dump(mode="json")
                         for x in sorted(bb.sections, key=lambda x: x.order)],
                        agent="design-director",
                        summary=f"composition: {len({s.archetype for s in bb.sections})} "
                                f"distinct archetype(s)")
    if rejected:
        yield Event(Stage.COMPOSE, "blocked",
                    f"composition decided but not recorded ({rejected.code}): "
                    f"{rejected.message}")
    shapes = {(s.width.value, s.archetype) for s in bb.sections}
    owner = next((x.id for x in bb.sections if x.carries_signature), "?")
    yield Event(Stage.COMPOSE, "progress",
                f"{applied} section(s) · {len(shapes)} distinct shape(s) · "
                f"{sum(1 for s in bb.sections if s.ground != GROUND_PAGE)} band(s) off the page ground · "
                f"signature: {owner} · "
                f"motion: {next((x.id for x in bb.sections if x.carries_motion), 'none')} · "
                f"{sum(len(x.treatments) for x in bb.sections)} treatment placement(s)")
    if rhythm:
        yield Event(Stage.COMPOSE, "progress", f"rhythm: {rhythm[:110]}")


def step_content(run: Run) -> Iterator[Event]:
    """Draft the copy for every section, and collect what it had to invent.

    CLAUDE.md §2's second differentiator. Before this stage the builder wrote
    copy inline from one line of instruction and recorded nothing about which
    claims were invented; the only user words that reached a page were hard
    constraints, pasted verbatim.

    It runs BEFORE the material gate rather than after, so the handful of
    questions it raises can ride along with the image questions instead of
    opening a fifth gate. §8 allows three, and a run with five stops is a run
    nobody finishes.

    Kept in a sidecar next to the asset plan rather than on the blackboard.
    §3 lists `content` as a blackboard field and it should end up there, but
    that is a schema change and this is not — the asset plan established the
    pattern and consistency is worth more here than purity.
    """
    from sparrow.agents.content_editor import ContentEditor
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    existing = load_content(run)
    blueprints = load_dir(run.dir / "blueprints")
    winners = load_winners(run)
    editor = ContentEditor()

    content: dict = {}
    asks = 0
    for section in sorted(bb.sections, key=lambda x: x.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None or not bp.slots:
            continue
        # A resumed run must not redraft copy the user has already answered on.
        prior = existing.get(section.id)
        if prior and prior.get("answered"):
            content[section.id] = prior
            continue

        # What the source's band for this section proves, and which real facts
        # the page already holds in sections drafted before this one — so the
        # ask is for something new, and a fact is spent in one place.
        proof = (winners.get(section.id) or {}).get("proof") or {}
        carried = [str(v) for e in content.values()
                   for k, v in (e.get("slots") or {}).items()
                   if (e.get("provenance") or {}).get(k) == "user_supplied"
                   and isinstance(v, str) and v.strip()]
        copy = editor.write(bb.brief, bb.constraints, bp, section_id=section.id,
                            proof=proof, facts=carried)
        content[section.id] = {
            "slots": copy.slots,
            "provenance": {k: v.value for k, v in copy.provenance.items()},
            "asks": [vars(a) for a in copy.asks],
            "answered": False,
        }
        asks += len(copy.asks)
        yield Event(Stage.CONTENT, "progress",
                    f"{section.id}: {len(copy.slots)} slot(s)"
                    + (f", {len(copy.asks)} to confirm" if copy.asks else ""))

    save_content(run, content)
    yield Event(Stage.CONTENT, "done",
                f"copy drafted for {len(content)} section(s) · "
                f"{asks} invented fact(s) to confirm")


def content_asks(run: Run) -> list[dict]:
    """Every unanswered ask across the run, flattened for the gate."""
    out: list[dict] = []
    for sid, entry in load_content(run).items():
        if entry.get("answered"):
            continue
        out += list(entry.get("asks") or [])
    return out


def record_content_answers(run: Run, answers: dict[str, str]) -> int:
    """Apply the gate's content answers. An empty answer keeps the draft.

    Returns how many slots the user actually replaced. Raises ValueError on an
    ask id that does not exist, because a silently ignored answer is worse than
    a refused one — the user typed a real fact about their business and would
    never learn it was dropped.
    """
    content = load_content(run)
    winners = load_winners(run)
    known = {a["id"] for e in content.values() for a in (e.get("asks") or [])}
    unknown = sorted(set(answers) - known)
    if unknown:
        raise ValueError(f"no such content ask(s): {', '.join(unknown)}")

    replaced = 0
    for entry in content.values():
        unanswered, answered_ = [], []
        for ask in list(entry.get("asks") or []):
            answer = (answers.get(ask["id"]) or "").strip()
            slot = ask["slot"]
            # The drafter keys a repeating slot without its `[]` marker and
            # returns a list; the answer must land on the same key in the same
            # shape, or the builder is handed the drafted list AND a string
            # under a second key. Measured: "BPCL, HDFC" stored beside the
            # drafted industries, and the wall tiled both.
            if answer:
                # Slots are keyed exactly as the blueprint names them, `[]`
                # included; a repeating slot takes a list.
                if slot.endswith("[]"):
                    items = [x.strip() for x in re.split(r"[\n;,]+|\s+(?:and|&)\s+", answer) if x.strip()]
                    entry["slots"][slot] = items or [answer]
                else:
                    entry["slots"][slot] = answer
                entry["provenance"][slot] = "user_supplied"
                replaced += 1
                answered_.append(dict(ask, answer=answer))
            else:
                unanswered.append(ask)
        # Kept on the record, not acted on here: this runs inside a request
        # handler, and the retraction is a model call per section. The asset
        # stage does it first thing, before anything is built on the claim.
        entry["unanswered"] = unanswered
        entry["answered_asks"] = answered_
        entry["asks"] = []
        entry["answered"] = True
    save_content(run, content)
    return replaced


ASSET_PLAN = "asset-plan.json"

# Per KIND, not one flat list. A logo is not an image with a different subject:
# `generate` is what put a fabricated brand on a real business's site and `skip`
# is what left the nav showing a lucide phone icon, so neither is offered.
IMAGE_DECISIONS = ("upload", "generate", "skip")

# `wordmark` is not "skip" wearing a different label. It produces no file, and it
# is a real answer: the name set in the design system's display typeface is a
# legitimate identity, and it is the one every company without a mark already
# uses. There is deliberately no `generate` — asking an image model for a logo is
# what produced the blank box, and a fabricated logo is a worse failure than
# none, because it is a fake identity on somebody's real business.
LOGO_DECISIONS = ("upload", "wordmark")

DECISIONS = IMAGE_DECISIONS          # kept: older callers mean the image list

LOGO_ASSET_ID = "nav-logo"
LOGO_BRIEF = ("Your logo — the mark that goes in the navigation and the footer, "
              "and inside any product screenshot we generate for you")


def _prominence(count: int, index: int):
    """How large an image sits in its section.

    One image owns the section it is in; after that the first is supporting and
    the rest are thumbnails. Derived in ONE place because the gate has to tell
    the user how large their upload will appear, and a gate that promises
    "dominant" for an image the curator then records as a thumbnail has told
    them something untrue.
    """
    from sparrow.blackboard.schema import Prominence

    if count == 1:
        return Prominence.DOMINANT
    return Prominence.SUPPORTING if index == 1 else Prominence.THUMBNAIL


def asset_plan(run: Run) -> list[dict]:
    """Every image the blueprints asked for, as a list that can be decided on.

    Enumerated once, at the gate, and written to disk; `step_assets` then
    EXECUTES this list rather than re-deriving it from the blueprints. Deriving
    it twice is how a gate ends up offering a choice about an image the curator
    never makes, or making one the user was never asked about.
    """
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    blueprints = load_dir(run.dir / "blueprints")
    out: list[dict] = []
    for section in sorted(bb.sections, key=lambda s: s.order):
        # THE LOGO IS NOT BLUEPRINT-DERIVED. It is asked for because the site
        # has a nav, not because a source site's nav happened to be measured as
        # carrying an image — the nav blueprint written for the project this was
        # built against lists no `Assets:` at all, so a plan that only reads
        # blueprints asks for no logo on the one page that needs one most.
        #
        # It also REPLACES whatever nav's blueprint listed rather than being
        # added to it. Nav is chrome: the only image in it is the mark. Leaving
        # the blueprint's briefs in alongside would put a `generate` back on the
        # nav, which is the exact failure removing nav from CHROME_SKIP_ASSETS
        # has to not reintroduce.
        if section.id == "nav":
            out.append({
                "id": LOGO_ASSET_ID, "section_id": "nav", "kind": "logo",
                "brief": LOGO_BRIEF,
                # Named, but it means nothing for a logo — a mark is sized by
                # the nav bar, not by the "dominant asset owns the section"
                # rule. `step_build` keeps logos out of the builder's asset
                # list entirely so that rule cannot fire on one.
                "prominence": "thumbnail",
                "decision": None, "upload": None,
            })
            continue
        bp = blueprints.get(section.blueprint_id)
        if bp is None or not bp.assets:
            continue
        if section.id in CHROME_SKIP_ASSETS:
            continue
        for i, brief in enumerate(bp.assets, 1):
            out.append({
                "id": f"{section.id}-{i}", "section_id": section.id,
                # A [video]-prefixed brief was still enumerated as an image, so
                # the gate offered a moving asset as a still and `_prominence`
                # could mark an ambient loop "dominant" — firing the builder's
                # "dominant asset owns the section" rule on decoration.
                "kind": "video" if brief.lstrip().lower().startswith("[video]") else "image",
                "brief": brief,
                "prominence": _prominence(len(bp.assets), i).value,
                "decision": None, "upload": None,
            })

    # THE ALLOCATED VIDEO, WHICH NO BLUEPRINT ASKS FOR ANY MORE. `compose` marks
    # one section, seeing the whole page and what the sources do; this is where
    # that decision becomes something the gate can offer and the curator can
    # execute. Appended rather than folded into the loop above because it is not
    # blueprint-derived — same reason the logo is not.
    mover = next((s for s in bb.sections if s.carries_motion), None)
    if mover is not None and mover.id not in CHROME_SKIP_ASSETS:
        role = mover.motion_role or "a silent ambient loop in the register the reference sites shoot theirs in"
        out.append({
            "id": f"{mover.id}-motion", "section_id": mover.id, "kind": "video",
            # The brief IS the role the composer wrote from the source facts —
            # not a fixed sentence about ambient texture. The composer saw the
            # frames; this did not.
            "brief": f"[video] {role}",
            "role": role,
            # Prominence from the same decision. "supporting" was hardcoded here
            # and it made every loop a backdrop: a 1920x1080 particle field
            # cropped to a 316px strip behind a paragraph, where the source ran
            # the same kind of footage full-bleed under its headline.
            "prominence": mover.motion_prominence or "supporting",
            # Whether the source's video has the headline on it — measured by
            # the scout, carried so the gate can tell atmosphere from content
            # without reading the role text.
            "under_heading": any(v.get("under_heading") for v in load_motion(run)
                                 if v.get("bleed") or v.get("under_heading")),
            "decision": None, "upload": None,
        })
    return out


def _kind(entry: dict) -> str:
    """A plan written before logos existed has no `kind`; those are all images."""
    return entry.get("kind") or "image"


def decisions_for(entry: dict) -> tuple[str, ...]:
    return LOGO_DECISIONS if _kind(entry) == "logo" else IMAGE_DECISIONS


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov"}
WINNERS = "winners.json"
READING = "reading.json"
MOTION = "motion.json"
SURFACES = "surfaces.json"
GROUNDS = "grounds.json"
DENSITY = "density.json"


def load_plan(run: Run) -> list[dict]:
    p = run.dir / ASSET_PLAN
    return json.loads(p.read_text()) if p.exists() else []


def save_plan(run: Run, plan: list[dict]) -> None:
    (run.dir / ASSET_PLAN).write_text(json.dumps(plan, indent=2))


def merged_plan(run: Run) -> list[dict]:
    """The plan re-enumerated, with everything already answered carried across.

    Two reasons this is not just `asset_plan`. A file posted before the gate was
    answered must survive a re-enumeration, or an upload is silently lost to a
    retry. And a project built before a slot existed must be able to pick it up:
    the voice-ai site was finished before the logo slot was added, so its saved
    plan has no `nav-logo` and re-reading the file would never grow one. A slot
    the blueprints ask for and the plan has never heard of is exactly the case
    this has to handle.
    """
    existing = {a["id"]: a for a in load_plan(run)}
    plan = asset_plan(run)
    for a in plan:
        prior = existing.get(a["id"])
        if prior:
            a["upload"] = prior.get("upload")
            a["decision"] = prior.get("decision")
            # `kind` is carried too, but only where the UPLOAD decided it. A
            # blueprint slot is enumerated as an image; posting an .mp4 to it is
            # what makes it a video, and re-enumeration was throwing that away —
            # the file stayed on disk as product-showcase-1.mp4 while the plan
            # went back to saying "image", so the curator generated a PNG over
            # the top of it and the page never saw the video.
            if prior.get("kind") == "video":
                a["kind"] = "video"
    return plan


def load_reading(run: Run) -> dict:
    f = run.dir / READING
    return json.loads(f.read_text()) if f.exists() else {}


def load_motion(run: Run) -> list[dict]:
    f = run.dir / MOTION
    return json.loads(f.read_text()) if f.exists() else []


def motion_facts(vids: list[dict]) -> str:
    """What the sources do with video — each one, in the terms that decide its
    role. Phrased as evidence for the composer; the role is the composer's."""
    if not vids:
        return ""
    sites = sorted({v.get("site") for v in vids})
    lines = [f"These sources carry {len(vids)} video(s) across {', '.join(sites)}. "
             f"Frames of them are attached after the section shots. Per video:"]
    for v in vids:
        size = "full-bleed" if v.get("bleed") else f"{v.get('w')}x{v.get('h')}"
        where = ("the opening section" if v.get("band") == 0 else
                 f"band {v['band']}" if v.get("band") is not None else "unplaced")
        kind = []
        if v.get("controls"):
            kind.append("has CONTROLS — a demo the reader presses play on")
        elif v.get("muted") and v.get("loop"):
            kind.append("muted looping autoplay — nothing to press")
        if v.get("under_heading"):
            kind.append("the HEADLINE SITS ON IT")
        if v.get("secs"):
            kind.append(f"{v['secs']}s")
        lines.append(f"  - {v.get('site')}: {size}, {where}; " + "; ".join(kind))
    lines.append(
        "Decide from these — and from the frames — what the video on THIS page is for, "
        "which section carries it, and how much of that section it owns. Put it where "
        "the sources put theirs, in the role theirs plays.")
    return "\n".join(lines)


def load_density(run: Run) -> dict[str, list[dict]]:
    f = run.dir / DENSITY
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except ValueError:
        return {}


def density_range(dens: dict[str, list[dict]], section_type: str) -> tuple[float, float] | None:
    """The sources' span of words per 1000px for this section type.

    Every source band of the type, not just the winner: a floor and ceiling
    the sources themselves set. Falls back to the span across ALL bands of all
    sources when only one band of the type was seen, so the range is still a
    measurement rather than a single point or a factor of mine.
    """
    rows = [r for r in dens.get(section_type, []) if r.get("words_per_k")]
    if len(rows) < 2:
        rows = [r for rs in dens.values() for r in rs if r.get("words_per_k")]
    if not rows:
        return None
    vals = [float(r["words_per_k"]) for r in rows]
    return (min(vals), max(vals))


def load_grounds(run: Run) -> dict[str, list[dict]]:
    f = run.dir / GROUNDS
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except ValueError:
        return {}


def ground_map(grounds: dict[str, list[dict]]) -> str:
    """Each source's bands down the page and what each sits on — measured.

    Runs of same-ground bands are collapsed so the eye lands on the changes:
    `bands 1-6 on #fdfcfc · band 7 on #111111 (dark) · bands 8-12 on #fdfcfc`.
    A source on one ground end to end reads as one run, which is also a fact.
    """
    if not grounds:
        return ""
    out = ["<source_grounds>",
           "What each reference site's bands SIT ON, in page order, measured off the "
           "rendered page. A band on its own ground or on a picture is where that "
           "page changes register; a page that never does is one that never does."]
    for site, rows in grounds.items():
        runs: list[list[dict]] = []
        for r in rows:
            key = (r.get("hex"), r.get("layered"))
            if runs and (runs[-1][0].get("hex"), runs[-1][0].get("layered")) == key:
                runs[-1].append(r)
            else:
                runs.append([r])
        bits = []
        for run_ in runs:
            a, b = run_[0]["band"] + 1, run_[-1]["band"] + 1
            span = f"band {a}" if a == b else f"bands {a}-{b}"
            g = run_[0]
            lum = g.get("lum")
            tone = ("dark" if isinstance(lum, (int, float)) and lum < 0.45 else "light")
            what = (f"on a PICTURE (canvas/video/image/gradient over {g.get('hex')})"
                    if g.get("layered") else f"on {g.get('hex')} ({tone})")
            head = f' "{g.get("heading")}"' if g.get("heading") and (g.get("differs") or g.get("layered")) else ""
            bits.append(f"{span} {what}{head}")
        out.append(f"  {site}: " + " · ".join(bits))
    out.append("</source_grounds>")
    return "\n".join(out)


def load_surfaces(run: Run) -> list[dict]:
    f = run.dir / SURFACES
    return json.loads(f.read_text()) if f.exists() else []


def surface_shots(run: Run, limit: int = 3) -> list[str]:
    """Canvas frames for the design director, biggest first."""
    surf = sorted(load_surfaces(run), key=lambda c: -(c.get("w", 0) * c.get("h", 0)))
    out = []
    for c in surf[:limit]:
        b = _b64(c.get("frame"))
        if b:
            out.append(b)
    return out


def surface_facts(surf: list[dict]) -> str:
    """What the sources draw on canvas — where, whether it moves, and whether
    the copy sits on it. Phrased as evidence for a designer; the decision is
    the designer's."""
    if not surf:
        return ""
    lines = [f"These sources draw {len(surf)} thing(s) on <canvas>. The LAST images "
             f"attached are frames of them. They are not sections; they are the layer a "
             f"page keeps where markup cannot express it."]
    for c in sorted(surf, key=lambda c: -(c.get("w", 0) * c.get("h", 0))):
        where = "full-bleed" if c.get("bleed") else f"{c.get('w')}x{c.get('h')}"
        pos = ("the opening section" if c.get("band") == 0 else
               f"band {c['band']}" if c.get("band") is not None else "across sections")
        lines.append(
            f"  - {c.get('site')}: {where}, {pos}, "
            + ("LIVE (it animates)" if c.get("live") else "static")
            + (" — the headline sits ON it; it is the page's atmosphere"
               if c.get("under_heading") else " — beside the copy, as an object"))
    lines.append(
        "If one of these is what makes its page feel the way it does, invent a "
        "treatment for it with `how` the builder can implement as written — an SVG "
        "filter, a CSS gradient stack, or a small canvas/requestAnimationFrame loop "
        "described precisely enough to write. `where` should say where the SOURCE "
        "puts it. Name the technique; do not describe the effect and stop.")
    return "\n".join(lines)


def load_winners(run: Run) -> dict:
    f = run.dir / WINNERS
    return json.loads(f.read_text()) if f.exists() else {}


def _b64(path: str | None) -> str | None:
    p = Path(path) if path else None
    if p is None or not p.is_file():
        return None
    import base64
    return base64.b64encode(p.read_bytes()).decode()


# A section's markup is the record of how its parts are arranged, which is the
# whole reason for showing it — but ramp.com's hero is 60 KB of build-tool class
# soup, and pasting that whole costs more than the screenshot beside it and
# teaches the builder less. Truncated to the opening structure, where the
# arrangement actually lives.
_MARKUP_CAP = 6000


def _source_markup(html: str | None) -> str:
    if not html:
        return ""
    html = html.strip()
    if len(html) <= _MARKUP_CAP:
        return html
    return html[:_MARKUP_CAP] + "\n… markup truncated …"


_SVG_BODY = re.compile(r"<svg\b[^>]*>.*?</svg>", re.S | re.I)
_DROP_TAGS = re.compile(r"<(script|style|noscript|template)\b[^>]*>.*?</\1>", re.S | re.I)
_ATTRS = re.compile(r"""<([a-zA-Z][\w-]*)((?:\s+[^\s=>]+(?:=(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*(/?)>""")
_CLASS = re.compile(r"""\bclass=(?:"([^"]*)"|'([^']*)')""")
_TEXT = re.compile(r">([^<]{1,})<")


def _skeleton(html: str | None, cap: int = 2200) -> str:
    """A source band's markup reduced to its STRUCTURE: tags, classes, counts.

    What the composer needs from a band is how its parts are arranged — how
    many columns, what each item is made of, what separates them — and that
    lives in the tag tree and the layout classes, not in the copy or the SVG
    paths. Text collapses to a word count, attributes to `class`, and svg to a
    single mark, so nine bands fit in the prompt where one raw band would not.
    """
    if not html:
        return ""
    h = _DROP_TAGS.sub("", html)
    h = _SVG_BODY.sub("<svg/>", h)

    def keep(m: re.Match) -> str:
        tag, attrs, close = m.group(1), m.group(2) or "", m.group(3)
        cm = _CLASS.search(attrs)
        cls = (cm.group(1) or cm.group(2) or "") if cm else ""
        # Layout classes only: framework prefixes stripped, CSS-variable
        # plumbing and build hashes dropped. `[--page-section-px:var(...)]`
        # says nothing about arrangement and costs forty characters.
        words = []
        for c in cls.split():
            c = re.sub(r"^(tw-|sm:tw-|md:tw-|lg:tw-)", lambda m: m.group(1).replace("tw-", ""), c)
            if "[--" in c or "var(" in c or re.search(r"[_-][0-9a-f]{5,}$", c):
                continue
            words.append(c)
        cls = " ".join(words[:8])
        return f"<{tag}{' class=' + repr(cls) if cls else ''}{'/' if close else ''}>"
    h = _ATTRS.sub(keep, h)
    h = _TEXT.sub(lambda m: f">{'·' + str(len(m.group(1).split())) + 'w' if m.group(1).strip() else ''}<", h)
    h = re.sub(r"\s+", " ", h).strip()
    # Empty decoration — the hairlines, corner dots and spacer divs a framework
    # wraps every band in — carries no structure. Removed until none is left.
    empty = re.compile(r"<(div|span|i|b)(?: class='[^']*')?></\1>")
    while True:
        h2 = empty.sub("", h)
        if h2 == h:
            break
        h = h2
    h = re.sub(r"<(div|span)></\1>", "", h)
    return h if len(h) <= cap else h[:cap] + " …"


def _page_sheet(run: Run, columns: int = 3) -> str | None:
    """The winning page as one contact sheet: its bands tiled into columns.

    NOT a full-page screenshot. capture.py works out why that fails: image
    tokens are (w*h)/750 after a resize to 1568px on the long edge, so a
    2880x13230 page becomes ~340px wide — a blur that costs real tokens and
    answers nothing. Tiling into columns keeps the aspect ratio near square, so
    the resize leaves each band wide enough to read as a band.

    What this is for is rhythm, not detail: how many sections, which are dense
    and which breathe, where the images fall, how the page paces itself
    top to bottom. The individual bands are passed alongside it for detail.
    """
    from PIL import Image

    src = run.dir / "sources"
    marker = src / "primary.txt"
    site = marker.read_text().strip() if marker.is_file() else None
    if not site:
        # Older projects have no marker. Most section wins is a guess, but a
        # better one than "first key in the file", which is just the hero's.
        from collections import Counter
        c = Counter(w["site"] for w in load_winners(run).values() if w.get("site"))
        site = c.most_common(1)[0][0] if c else None
    if not site:
        return None
    host = site.replace(".", "_").replace("https://", "").replace("/", "")
    bands = sorted(src.glob(f"{host}-b*.png"))
    if not bands:
        return None

    cached = src / f"{host}-sheet.png"
    if not cached.exists():
        W = 460                       # per-column width after scaling
        GAP = 12
        ims = []
        for b in bands:
            im = Image.open(b).convert("RGB")
            ims.append(im.resize((W, max(1, round(im.height * W / im.width)))))
        total = sum(i.height + GAP for i in ims)
        per_col = total / columns
        cols: list[list] = [[]]
        used = 0.0
        for im in ims:
            if used > per_col and len(cols) < columns:
                cols.append([])
                used = 0.0
            cols[-1].append(im)
            used += im.height + GAP
        height = max(sum(i.height + GAP for i in c) for c in cols)
        sheet = Image.new("RGB", (columns * (W + GAP), int(height)), (255, 255, 255))
        for ci, col in enumerate(cols):
            y = 0
            for im in col:
                sheet.paste(im, (ci * (W + GAP), y))
                y += im.height + GAP
        sheet.save(cached)
    return _b64(str(cached))


def _winner_shots(run: Run, limit: int = 4) -> list[str]:
    """The winning source's sections, as images, biggest first.

    Capped: the design agent needs to SEE the page it is designing from, not
    every band of it. Four sections at ~1,700 tokens each is the shape of the
    thing without paying for the whole site.
    """
    out: list[str] = []
    for _t, w in load_winners(run).items():
        b = _b64(w.get("shot"))
        if b:
            out.append(b)
        if len(out) >= limit:
            break
    return out


def step_asset_gate(run: Run) -> Iterator[Event]:
    """Ask, per image, whose it is.

    CLAUDE.md §2 names real material as the differentiator, and until this gate
    existed there was no moment in the run at which a user could hand the system
    a file. The curator read each blueprint's asset briefs and generated all of
    them; `Provenance` carried three values and recorded one. A differentiator
    with no entry point is not a differentiator.

    Per asset rather than once for the whole run, because the answer genuinely
    differs per asset: a founder has a real dashboard screenshot for the hero and
    nothing at all for the integrations strip. One global choice forces them to
    either fabricate the second or lose the first.

    §8 wants concrete options, so each asset carries the brief in the
    blueprint's own words, the section it lands in, and its prominence — "this
    one will be the largest thing on the page" is answerable; "asset hero-1" is
    not.
    """
    existing = load_plan(run)
    plan = merged_plan(run)

    facts = content_asks(run)

    if not plan and not facts:
        save_plan(run, plan)
        yield Event(Stage.GATE_ASSETS, "done",
                    "no blueprint asked for imagery, and the copy invented nothing")
        return

    decided = {a["id"]: a.get("decision") for a in existing}
    if plan and all(decided.get(a["id"]) for a in plan) and not facts:
        # Already answered — a resumed run must not ask the same question twice.
        save_plan(run, existing)
        yield Event(Stage.GATE_ASSETS, "done",
                    f"{len(plan)} image(s) already decided")
        return

    save_plan(run, plan)
    upload_url = f"/projects/{run.project_id}/assets"
    parts = []
    if plan:
        parts.append(f"{len(plan)} image(s) go on this page — for each one: use "
                     "your own file, have one generated, or leave it out")
    if facts:
        parts.append(f"{len(facts)} line(s) of the copy state something about your "
                     "business that we had to make up — confirm or correct them, "
                     "or leave the draft as it is")

    raise Halt(GateRequest(
        Stage.GATE_ASSETS,
        ". ".join(parts) + ".",
        options=[{
            "kind": "fact",
            "ask_id": f["id"],
            "section_id": f["section_id"],
            "slot": f["slot"],
            "question": f["question"],
            "draft": f["draft"],
            "invented": f["invented"],
            "source_example": f["source_example"],
            "choices": [
                {"choice": "answer",
                 "label": "Give the real answer",
                 "detail": "Used verbatim, and never redrafted afterwards.",
                 "field": "text"},
                {"choice": "keep",
                 "label": "Keep the draft as written"},
            ],
        } for f in facts] + [{
            "kind": _kind(a),
            "asset_id": a["id"],
            "section_id": a["section_id"],
            "brief": a["brief"],
            "prominence": a["prominence"],
            "uploaded": bool(a["upload"]),
            "choices": _choices_for(a, upload_url),
        } for a in plan],
        artifacts=[],
    ))


def _choices_for(a: dict, upload_url: str) -> list[dict]:
    """The choices the gate shows for one asset, by kind.

    This must agree with `decisions_for`, which is what `record_asset_decisions`
    validates against. It did not: the dispatch was `image → image choices,
    everything else → logo choices`, so a VIDEO slot was presented as "Upload
    our logo / set the name as a wordmark" while the validator would only ever
    accept upload / generate / skip for it. The one user who reached that gate
    could not answer it correctly from what they were shown.
    """
    kind = _kind(a)
    if kind == "logo":
        return _logo_choices(a, upload_url)
    if kind == "video":
        return _video_choices(a, upload_url)
    return _image_choices(a, upload_url)


def _video_choices(a: dict, upload_url: str) -> list[dict]:
    """Same three answers as an image; the words come from what the source's
    video IS, which the composer decided and `asset_plan` carried in `role`.

    The order changes with the role, and that is the whole point. A video model
    renders convincing footage and gibberish UI: for atmosphere that is exactly
    right, for a product recording it is the §2 failure on film. So when the
    source's video is a recording of its product, the first thing offered is
    the user's own — and generate stays on the list, because whether to accept
    the gibberish is theirs to decide, not this function's.
    """
    role = (a.get("role") or "").strip()
    # "Is this a recording of the product" is not read off the role text by a
    # keyword list of mine; the composer decided the role AND the prominence
    # from the scout's facts. A dominant, non-atmospheric video is one the
    # source shows as content — and content is the user's to supply.
    recording = (a.get("prominence") == "dominant"
                 and not (a.get("under_heading") or False))
    upload = {
        "choice": "upload",
        "label": "Use our own video",
        "detail": ("Used exactly as it is — a moving asset is never restyled, "
                   "scrubbed or cropped." +
                   (" The reference sites show their actual product here, and a "
                    "generated clip cannot show yours — its interface will be "
                    "invented. A screen recording is the real thing."
                    if recording else " A short silent loop works best.")),
        "accepts": "MP4, WebM or MOV",
        "post_file_to": f"{upload_url}/{a['id']}",
    }
    generate = {
        "choice": "generate",
        "label": "Generate one",
        "detail": (f"Shot the way the reference sites shoot theirs — {role}. "
                   if role else "Shot to match the reference sites' own footage. ")
                  + ("Any interface in frame will be invented, not yours. "
                     if recording else "")
                  + "Takes a few minutes.",
    }
    skip = {"choice": "skip",
            "label": "No video — build the section from type and layout"}
    return [upload, generate, skip] if recording else [generate, upload, skip]


def _image_choices(a: dict, upload_url: str) -> list[dict]:
    return [
        {"choice": "upload",
         "label": "Use my own image",
         "detail": "Restyled to the chosen design direction. Any text it "
                   "gains that the original did not have is rejected.",
         "post_file_to": f"{upload_url}/{a['id']}"},
        {"choice": "generate",
         "label": "Generate one from this description"},
        {"choice": "skip",
         "label": "No image — build the section from type and layout"},
    ]


def _logo_choices(a: dict, upload_url: str) -> list[dict]:
    """Two, and only two.

    There is no `generate`: a logo an image model drew is a fake identity on a
    real business's site, and the one time it was tried the output was a
    1536x1024 lockup rendered as a full-width blank box above the hero. There is
    no `skip` either — skipping is what left the nav showing a lucide phone icon
    with `aria-label="Platform home"` on all eight measured projects. A site has
    a name whether or not it has a mark, so the fallback is the name.
    """
    return [
        {"choice": "upload",
         "label": "Upload our logo",
         "detail": "Used as it is. Recoloured or placed on a neutral chip if it "
                   "needs it, never redrawn — an image model asked to restyle a "
                   "logo redraws the letterforms, and that is your trademark "
                   "coming back subtly wrong.",
         "accepts": "PNG, JPEG, WebP or SVG",
         "post_file_to": f"{upload_url}/{a['id']}"},
        {"choice": "wordmark",
         "label": "No logo file — set the name as a wordmark",
         "detail": "The product name in the design direction's display "
                   "typeface. No file, nothing invented."},
    ]


def record_asset_decisions(run: Run, decisions: dict[str, str]) -> list[dict]:
    """Write the gate's answer onto the plan. Raises ValueError on a bad answer."""
    plan = load_plan(run)
    known = {a["id"] for a in plan}
    unknown = sorted(set(decisions) - known)
    if unknown:
        raise ValueError(f"no such asset(s): {', '.join(unknown)}")
    for a in plan:
        allowed = decisions_for(a)
        choice = decisions.get(a["id"], a.get("decision"))
        if choice is None:
            # Distinct from a wrong answer: nothing was said about this one.
            # The gate lists every slot and the interface has to answer all
            # of them — an unanswered slot is how the frontend's silent drop
            # of the logo and video rows surfaced, as a 400 that named the
            # wrong problem.
            raise ValueError(
                f"{a['id']} ({_kind(a)}, {a['section_id']}) was not answered — it "
                f"needs one of {', '.join(allowed)}. Every image is decided "
                "individually, including the logo and any video; there is no "
                "answer for all of them.")
        if choice not in allowed:
            # Refused, never coerced. `generate` on a logo is the single answer
            # this gate exists to make unreachable, and quietly reading it as
            # `wordmark` would hide from the caller that it asked for something
            # the system will not do.
            raise ValueError(
                f"{a['id']} needs one of {', '.join(allowed)} — every image is "
                "decided individually, there is no answer for all of them"
                + (" · a logo is never generated and never skipped: it is your "
                   "mark or it is your name" if _kind(a) == "logo" else ""))
        if choice == "upload" and not a.get("upload"):
            raise ValueError(
                f"{a['id']} was answered 'upload' but no file has been posted to "
                f"/projects/{run.project_id}/assets/{a['id']} yet")
        a["decision"] = choice
    save_plan(run, plan)

    # One decision per image, not one for the batch. Provenance downstream is
    # per asset — a founder uploads a real dashboard for the hero and skips the
    # integrations strip — so a single "asset gate answered" line cannot say
    # which of those two produced the file that shipped. The brief is the
    # blueprint's own words, not the user's, so it is safe to quote.
    for a in plan:
        rejected = _note(run, agent="user@gate:assets",
                         summary=f"{a['id']} ({a['section_id']}, "
                                 f"{a['prominence']}): {a['decision']}")
        if rejected:
            telemetry_note(run, "record_asset_decisions", rejected)
            break
    return plan


def record_upload(run: Run, asset_id: str, filename: str, data: bytes) -> dict:
    """Store a user's file against one asset in the plan.

    SVG is accepted for a LOGO and only for a logo. It is the format the hard
    rule actually wants — an SVG mark recolours through `currentColor` or a CSS
    filter with no pixels touched at all, which is the strongest possible
    version of "recoloured, never redrawn". Pillow cannot open one, so it is
    validated as XML with an <svg> root instead of being handed to `Image.open`,
    which would reject every logo worth having.

    It is NOT accepted for a content image: everything downstream of an image
    upload — the scrub's vision pass, the restyle, `derive_variants` — is raster
    work, and an SVG would fail at whichever of them ran first, several minutes
    and one gate later than here.
    """
    # Merged, so a slot the blueprints ask for can be uploaded to even on a
    # project whose saved plan predates it. Loading the file instead rejected
    # the logo on every site built before the logo slot existed — which is all
    # of them.
    plan = merged_plan(run)
    entry = next((a for a in plan if a["id"] == asset_id), None)
    if entry is None:
        raise ValueError(f"no such asset {asset_id!r} in this run's plan")

    up = run.dir / "uploads"
    up.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower() or ".png"

    from sparrow.specimen import is_svg

    if suffix in VIDEO_SUFFIXES:
        # A video is passed through untouched. Every other upload path here is
        # raster work over one frame — the scrub's vision pass, the restyle,
        # `derive_variants` — and none of it means anything for a moving asset.
        name = f"{asset_id}{suffix}"
        (up / name).write_bytes(data)
        entry["upload"] = name
        entry["kind"] = "video"
        save_plan(run, plan)
        return entry

    if is_svg(data):
        if _kind(entry) != "logo":
            raise ValueError(
                f"{filename} is an SVG. SVG is accepted for your logo, but a "
                "content image is scrubbed, restyled and resized as pixels — "
                "send a PNG, JPEG or WebP for this one")
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(data.decode("utf-8", "strict"))
        except (ET.ParseError, UnicodeDecodeError) as e:
            raise ValueError(f"{filename} is not readable SVG: {e}") from e
        if not root.tag.endswith("svg"):
            raise ValueError(f"{filename} is XML but its root is not <svg>")
        name = f"{asset_id}.svg"
        (up / name).write_bytes(data)
        entry["upload"] = name
        save_plan(run, plan)
        return entry

    from PIL import Image, UnidentifiedImageError

    name = f"{asset_id}{suffix}"
    (up / name).write_bytes(data)
    try:
        with Image.open(up / name) as im:
            im.verify()
    except (UnidentifiedImageError, OSError) as e:
        (up / name).unlink(missing_ok=True)
        raise ValueError(f"{filename} is not a readable image: {e}") from e

    entry["upload"] = name
    save_plan(run, plan)
    return entry


def _logo_size(path: Path) -> tuple[int, int]:
    """Intrinsic size, for both formats a logo may arrive in.

    `next/image` needs width and height even for an SVG, so an SVG's viewBox is
    read rather than defaulted — a 0x0 asset makes the component throw at build
    time, which is a broken page rather than a slightly wrong one.
    """
    if path.suffix.lower() == ".svg":
        import xml.etree.ElementTree as ET

        root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
        box = (root.get("viewBox") or "").replace(",", " ").split()
        if len(box) == 4:
            try:
                return round(float(box[2])), round(float(box[3]))
            except ValueError:
                pass

        def dim(attr: str, fallback: int) -> int:
            raw = "".join(c for c in (root.get(attr) or "") if c.isdigit() or c == ".")
            try:
                return round(float(raw)) or fallback
            except ValueError:
                return fallback

        return dim("width", 240), dim("height", 64)

    from PIL import Image

    with Image.open(path) as im:
        return im.size


def reset_assets(run: Run, asset_ids: list[str]) -> list[str]:
    """Drop named assets so a re-advance produces them again.

    The counterpart of `reset_sections`, and needed for the same reason one
    level down: `step_assets` now KEEPS an asset it has already produced, so
    without this there is no way to say "make the hero again" — which is exactly
    what uploading a logo asks for, because every generated product surface is
    given the logo as a reference and the ones made before it was uploaded carry
    invented branding.

    The record and the file are removed together. A record without a file
    resumes into a 404; a file without a record is published by nothing and
    quietly takes disk.
    """
    bb = _bb(run)
    known = {a.id for a in bb.assets}
    unknown = sorted(set(asset_ids) - known)
    if unknown:
        raise ValueError(f"no such asset(s) on this blackboard: {', '.join(unknown)}")

    dropped = [a for a in bb.assets if a.id in set(asset_ids)]
    kept = [a for a in bb.assets if a.id not in set(asset_ids)]
    for a in dropped:
        for rel in [a.path, *a.variants.values()]:
            (run.workspace / "public" / rel).unlink(missing_ok=True)

    rejected = _replace(run, "/assets", [a.model_dump(mode="json") for a in kept],
                        agent="user@reset",
                        summary=f"{len(dropped)} asset(s) dropped for re-making: "
                                + ", ".join(a.id for a in dropped))
    if rejected:
        telemetry_note(run, "reset_assets", rejected)
    return [a.id for a in dropped]


def _checkpoint_assets(run: Run, made: list) -> None:
    """Write the assets produced SO FAR, so a later crash does not discard them.

    `step_assets` recorded nothing until the whole loop finished. Measured on
    meridian-v2: the tenth asset raised, and the nine images already generated,
    written to disk and paid for were never recorded — so `prior`, which exists
    precisely to keep an already-produced asset from being made twice, read an
    empty list on resume and every one of them would have been regenerated at
    full price. Nine successful network calls thrown away by the tenth failing.

    Deliberately a plain write rather than a `Store.apply` transition. It is a
    crash checkpoint, not a decision: the authoritative transition still happens
    once at the end of the stage, so the decision log keeps one entry for the
    stage instead of one per image.
    """
    f = run.dir / "blackboard.json"
    try:
        bb = json.loads(f.read_text())
        bb["assets"] = [a.model_dump(mode="json") for a in made]
        f.write_text(json.dumps(bb, indent=2))
    except (OSError, ValueError):
        pass          # a checkpoint that cannot be written must not kill the run


def _retract_unanswered_claims(run: Run) -> Iterator[Event]:
    """Redraft every slot whose proof ask went unanswered, before the build.

    A stats slot drafted as "10M+ conversations" with the question unanswered
    is a claim the business never made. The old contract kept the draft; this
    rewrites it to say nothing unconfirmed, one call per section that needs it.
    """
    from sparrow.agents.content_editor import ContentEditor, retract_unanswered

    content = load_content(run)
    todo = {sid: e for sid, e in content.items()
            if e.get("unanswered") or e.get("answered_asks")}
    if not todo:
        return
    editor = ContentEditor()
    for sid, entry in todo.items():
        try:
            new = retract_unanswered(editor, sid, entry.get("slots") or {},
                                     entry.get("unanswered") or [],
                                     entry.get("answered_asks") or [])
        except Exception as e:  # noqa: BLE001 — a failed retraction must not ship the claim
            new = {}
            yield Event(Stage.ASSETS, "progress",
                        f"{sid}: retraction failed ({type(e).__name__}) — claims cleared")
        # `new` is keyed as the model keys things — without `[]`; the record
        # is keyed as the blueprint names them. Every slot the rewrite returned
        # is applied, not only the one the ask pointed at: a quote nobody
        # confirmed has a company, a name and a role in sibling slots.
        by_key = {(k[:-2] if k.endswith("[]") else k): k for k in entry["slots"]}
        for k, v in new.items():
            raw = by_key.get(k)
            if raw is not None and (entry["provenance"] or {}).get(raw) != "user_supplied":
                entry["slots"][raw] = v
                entry["provenance"][raw] = "drafted"
        for a in entry.get("unanswered") or []:
            slot = a["slot"]
            if (slot[:-2] if slot.endswith("[]") else slot) not in new and slot in entry["slots"]:
                # No rewrite came back: the claim still cannot ship. An empty
                # slot is a visible hole the inspector will name; a fabricated
                # number is an invisible one nobody will.
                entry["slots"][slot] = [] if isinstance(entry["slots"][slot], list) else ""
                entry["provenance"][slot] = "drafted"
        yield Event(Stage.ASSETS, "progress",
                    f"{sid}: {len(entry.get('unanswered') or [])} unconfirmed claim(s) "
                    f"retracted, {len(entry.get('answered_asks') or [])} answer(s) reconciled")
        entry["unanswered"] = []
        entry["answered_asks"] = []
    save_content(run, content)


def step_assets(run: Run) -> Iterator[Event]:
    """Execute the plan the asset gate decided. One image, one provenance.

    UPLOAD is also the only path carrying anything real about anybody else, so
    it is the only one SCRUBBED — and the scrub runs before the restyle, because
    the restyle is what puts the file in front of a third party.

    UPLOAD is the only path that can ship a claim the user never made, so it is
    the only one gated: the restyle is checked for text fidelity, and a restyle
    that invented words is discarded in favour of the user's untouched original.
    Their real screenshot, unstyled, beats a beautiful one that says something
    about their product that is not true. The rejection is recorded on the asset
    rather than swallowed.
    """
    yield from _retract_unanswered_claims(run)

    from sparrow.agents.curator import Curator, derive_variants
    from sparrow.blackboard.schema import Asset, AssetKind, Prominence, Provenance
    from PIL import Image

    bb = _bb(run)
    plan = merged_plan(run)
    # A slot with a file and no answer is an upload. The gate is still the place
    # the choice is made, but a project past that gate has no way to answer one
    # — and refusing to execute a file the user went and found, because a field
    # beside it says null, is the wrong reading of what they did.
    for a in plan:
        if a.get("upload") and not a.get("decision"):
            a["decision"] = "upload"
    if not plan:
        # No gate ran: a project created before the asset gate existed, or a
        # blueprint set that asks for no imagery. Generating is what this stage
        # did before the gate, so an old project resumes with its old behaviour
        # rather than stalling on a question nobody was asked.
        plan = [dict(a, decision="generate") for a in asset_plan(run)]
        save_plan(run, plan)

    public = run.workspace / "public" / "assets"
    public.mkdir(parents=True, exist_ok=True)
    cur = Curator()
    made: list[Asset] = []

    # THE LOGO IS PRODUCED FIRST, because two later things need the file: the
    # builder puts it in the nav and the footer, and every GENERATED product
    # screenshot is given it as a reference so the branding inside the image is
    # the user's own. Measured on the eight real projects: with no logo and no
    # name, a generated hero invented a company called "Off-Hook" that appears
    # nowhere else, so the uploaded mark and the generated imagery advertised
    # two different businesses.
    logo_entry = next((a for a in plan if _kind(a) == "logo"), None)
    logo_bytes: bytes | None = None

    # A section already produced, with its file still on disk, is KEPT. Same
    # rule as `step_build`, for the same reason and a larger bill: re-running
    # this stage on a project that already has seven assets is seven image calls
    # and several vision passes, paid again to produce what is already there.
    # A deliberate re-make goes through `reset_assets`, which removes the record
    # and the file together.
    prior = {a.id: a for a in bb.assets if (run.workspace / "public" / a.path).exists()}

    # ---- the generations, started together instead of one after another ------
    #
    # Measured on meridian-engine: 15 images, mean 70s, min 54s, max 116s —
    # 17.6 minutes in which the harness did nothing but wait on one socket at a
    # time. The work is network-bound, so threads are the right tool and there is
    # no async rewrite to do.
    #
    # This deliberately does NOT restructure the loop below. Every yield, every
    # branch and every ordering stays exactly as it was; only the waiting moves.
    # A future raises at `.result()` in the same place the direct call used to
    # raise, so failure behaviour is unchanged and one bad asset does not take
    # the other fourteen with it.
    #
    # The LOGO is read before anything is submitted, not produced by the pool:
    # every generated surface is given the mark as a branding reference, so it
    # is a barrier, not a peer. It is a file copy, so the barrier costs nothing.
    if logo_entry is not None and logo_entry.get("decision") == "upload" \
            and logo_entry.get("upload"):
        try:
            logo_bytes = (run.dir / "uploads" / logo_entry["upload"]).read_bytes()
        except OSError:
            logo_bytes = None

    # THE SOURCE'S OWN FOOTAGE, so the loop is shot the way theirs is. The
    # curator has read a source frame and steered generation by it since the
    # vision pass was written — and this stage never handed it one, so every
    # loop in every real run was generated blind from a one-line brief. The
    # result was stock: a woman at three monitors, code legible and head-on,
    # the design system's colour NAME painted across the screens. The frame
    # that would have prevented it was on disk the whole time.
    #
    # The section's own winning source first, then the primary, then any.
    def _source_video(section_id: str, role: str = "",
                      prominence: str = "") -> dict | None:
        """The source video this loop is modelled on.

        Chosen to match what the composer decided the video IS, not by a
        preference of this function's. The first version ranked muted+loop
        first — an "ambient before demo" heuristic — and on voiceowl that
        picked sarvam's wordmark-over-Taj-Mahal loop over elevenlabs' footage
        of a woman on a phone call, for a role the composer had written as "a
        live agent call recording". The frame the curator read had nothing to
        do with the role, and the clip came out as an abstract render.

        So: the section's own winning source first, then the primary, then
        the rest — and within that, the video whose measured shape agrees with
        the decided prominence. Dominant video is content: prefer the ones the
        source shows as content (controls, or large, or the headline is NOT on
        it). Supporting/thumbnail video is texture: prefer the muted loops.
        """
        # A 22x24 <video> is an animated icon, not footage — cursor.com has one.
        vids = [v for v in load_motion(run)
                if v.get("frame") and v.get("w", 0) >= 240 and v.get("h", 0) >= 160]
        if not vids:
            return None
        won = (load_winners(run).get(section_id) or {}).get("site")
        primary = load_reading(run).get("site")
        def site_rank(v):
            return 0 if v.get("site") == won else 1 if v.get("site") == primary else 2
        content = (prominence == "dominant")
        def shape_rank(v):
            ambient = bool(v.get("muted") and v.get("loop") and not v.get("controls"))
            big = v.get("w", 0) * v.get("h", 0)
            # content wants non-ambient and large; texture wants ambient
            return (0 if (ambient != content) else 1, -big)
        vids.sort(key=lambda v: (site_rank(v), *shape_rank(v)))
        for v in vids:
            if Path(v["frame"]).is_file():
                return v
        return None

    def _produce(a: dict) -> bytes:
        brief = a["brief"].lstrip()
        if brief.lower().startswith("[video]"):
            src = _source_video(a["section_id"], a.get("role", ""), a.get("prominence", ""))
            frame = Path(src["frame"]).read_bytes() if src else None
            # The source video's own aspect, not a fixed "wide": a portrait loop
            # in a rail wants 9:16, and generating 16:9 for it and letting CSS
            # crop is how a rail becomes a letterbox.
            shape = ("tall" if src and src.get("h", 0) > src.get("w", 0) * 1.15
                     else "wide")
            return cur.motion(brief[7:].strip(), bb.design_system,
                              frame=frame, shape=shape, role=a.get("role", ""))
        return cur.generate(a["brief"], bb.design_system,
                            product_name=bb.brief.product_name, logo=logo_bytes)

    def _fresh(a: dict) -> bool:
        keep = prior.get(a["id"])
        return not (keep is not None and keep.kind.value == _kind(a))

    queue = [a for a in plan
             if (a.get("decision") or "generate") == "generate"
             and _kind(a) != "logo" and _fresh(a)]
    futures: dict[str, object] = {}
    pool = None
    if len(queue) > 1:
        from concurrent.futures import ThreadPoolExecutor

        # Bounded. The provider publishes no concurrency ceiling, and a burst of
        # fifteen is how you find out it has one.
        pool = ThreadPoolExecutor(max_workers=int(
            os.environ.get("SPARROW_ASSET_WORKERS", "4")))
        futures = {a["id"]: pool.submit(_produce, a) for a in queue}
        yield Event(Stage.ASSETS, "progress",
                    f"{len(queue)} generations started {pool._max_workers} at a time")

    def produced(a: dict) -> bytes:
        """The bytes for one asset — from the pool if it was queued."""
        f = futures.get(a["id"])
        return f.result() if f is not None else _produce(a)

    for a in plan:
        # Everything finished before this one, persisted. If the asset below
        # raises, the work already paid for survives the crash and `prior` keeps
        # it on the next attempt.
        _checkpoint_assets(run, made)
        aid, decision = a["id"], a.get("decision") or "generate"
        kind = _kind(a)

        if kind == "logo" and decision == "wordmark":
            yield Event(Stage.ASSETS, "progress",
                        "no logo file — the nav and footer set your name as a "
                        "wordmark in the display typeface")
            continue

        if decision == "skip":
            yield Event(Stage.ASSETS, "progress",
                        f"{aid} skipped — the builder composes this section from "
                        "type and layout")
            continue

        keep = prior.get(aid)
        if keep is not None and keep.kind.value == kind:
            made.append(keep)
            if kind == "logo":
                logo_bytes = (run.workspace / "public" / keep.path).read_bytes()
            yield Event(Stage.ASSETS, "progress",
                        f"{aid}: already produced ({keep.provenance.value}) — kept")
            continue

        if kind == "logo":
            # RECOLOURED, NEVER REDRAWN. The file is copied through untouched.
            # It does not go to `Curator.restyle` — an image model asked to
            # restyle a mark redraws the letterforms, and unlike a redrawn
            # dashboard that is a trademark come back subtly wrong, published on
            # the owner's own site. Everything that makes it sit on the design
            # system's ground is CSS and SVG over the file, decided by
            # `logo_placement` from measured luminance and carried out by the
            # builder.
            #
            # It is not SCRUBBED either. The scrub substitutes person names and
            # org names, and a logo is very often exactly that — a founder's
            # name is the mark. There is no customer data in a logo to protect
            # and a great deal of trademark to destroy.
            src = run.dir / "uploads" / a["upload"]
            logo_bytes = src.read_bytes()
            path = public / f"{aid}{src.suffix.lower()}"
            path.write_bytes(logo_bytes)
            w, h = _logo_size(path)
            made.append(Asset(
                id=aid, section_id=a["section_id"], kind=AssetKind.LOGO,
                brief=a["brief"], prominence=Prominence(a["prominence"]),
                provenance=Provenance.USER_SUPPLIED,
                path=f"assets/{path.name}", width=w, height=h,
                # No variants. `derive_variants` centre-crops to 1600x900,
                # 800x800 and 720x900 — on a wordmark that is three pictures of
                # the middle four letters.
                variants={}, rejected=[], scrubbed=[],
            ))
            yield Event(Stage.ASSETS, "progress",
                        f"{aid}: your logo, used as it is — never sent to the "
                        f"image model, never redrawn")
            continue

        # ONLY the uploaded case. `kind` became "video" for the composer's
        # allocated loop too, which has no upload — and this branch's first act
        # is to open one, so a generated video crashed the stage on
        # `run.dir / "uploads" / None`. A generated loop falls through to the
        # `[video]`-prefix branch below, which is the path that calls the model.
        if _kind(a) == "video" and decision == "upload" and a.get("upload"):
            src = run.dir / "uploads" / a["upload"]
            dest = public / f"{aid}{src.suffix}"
            dest.write_bytes(src.read_bytes())
            made.append(Asset(
                id=aid, section_id=a["section_id"], kind=AssetKind.VIDEO,
                brief=a["brief"], prominence=Prominence(a["prominence"]),
                provenance=Provenance.USER_SUPPLIED,
                path=f"assets/{dest.name}",
            ))
            yield Event(Stage.ASSETS, "progress",
                        f"{aid}: your video, used as it is — nothing here "
                        f"generates, scrubs or restyles a moving asset")
            continue

        path = public / f"{aid}.png"
        rejected: list[str] = []
        scrubbed: list[str] = []

        if decision == "upload":
            original = (run.dir / "uploads" / a["upload"]).read_bytes()
            # FIRST, before any other network call. `restyle` posts the file to
            # a third-party image model and the result is published at the
            # preview URL; a scrub after either is a scrub of a copy.
            scrub = cur.scrub(original)
            scrubbed = list(scrub.changed)
            if scrubbed:
                # Written beside their upload so the substitution is theirs to
                # check. The report says what CATEGORY changed and never the
                # value it changed from — see `curator.Scrub`.
                (run.dir / "uploads" / f"{aid}--scrubbed.png").write_bytes(scrub.image)
                yield Event(Stage.ASSETS, "progress",
                            f"{aid}: real values substituted out of your screenshot "
                            f"before anything else saw it — {', '.join(scrubbed)}")

            restyled = cur.restyle(scrub.image, bb.design_system)
            # Compared SCRUBBED-against-restyled, never original-against-restyled.
            # The gate asks whether the image model invented copy, so the ground
            # truth is what the image model was GIVEN. Against the original,
            # every substitution the scrub made reads as a word the restyle
            # invented, and every legitimate restyle of a dashboard is rejected.
            # The lines come from the scrub, which already read its own output
            # back to verify itself.
            fidelity = cur.check_fidelity(scrub.lines, restyled)
            if fidelity.ok:
                path.write_bytes(restyled)
                provenance = Provenance.RESTYLED
                yield Event(Stage.ASSETS, "progress",
                            f"{aid} restyled from your file — text fidelity holds")
            else:
                # One attempt, no retry. The failure is the model inventing copy,
                # and a second roll of the same prompt is not evidence it will
                # invent less — it is another image call against the same odds.
                # What falls back is the SCRUBBED image, not the upload: the
                # restyle failing is no reason to publish the customer data.
                _write_png(scrub.image, path, Image)
                provenance = Provenance.USER_SUPPLIED
                rejected.append(f"restyle rejected — {fidelity.reason()}")
                yield Event(Stage.ASSETS, "blocked",
                            f"{aid}: restyle invented text ({fidelity.reason()}) — "
                            "shipping your own screenshot instead")
        elif a["brief"].lstrip().lower().startswith("[video]"):
            # A moving asset. Separate branch rather than a flag on the image
            # path, because almost nothing downstream is shared: no Pillow open,
            # no derived crops (a card crop of a loop is meaningless), no
            # branding check (there is no legible brand in footage that is
            # deliberately out of focus), and a different file extension.
            path = path.with_suffix(".mp4")
            path.write_bytes(produced(a))
            # MEASURED, not assumed. This said 1280x720 whatever the file was,
            # and the builder is told to respect an asset's aspect ratio — so a
            # 1920x1080 loop arrived described as 720p and a portrait rail would
            # arrive described as a landscape banner.
            vw, vh = _video_size(path)
            made.append(Asset(
                id=aid, section_id=a["section_id"], kind=AssetKind.VIDEO,
                brief=a["brief"], prominence=Prominence(a["prominence"]),
                provenance=Provenance.GENERATED,
                path=f"assets/{path.name}", width=vw, height=vh,
            ))
            yield Event(Stage.ASSETS, "progress",
                        f"{aid} generated · a silent ambient loop, not a demo"
                        + (f" · {cur.last_motion_note}" if cur.last_motion_note else ""))
            continue
        else:
            # The name and the mark both go in. A generated product surface
            # shows branding somewhere — a sidebar header, a window title, a
            # browser tab — and with nothing given it invents one, which is
            # where "Off-Hook" came from on a site whose owner never used that
            # word.
            made_bytes = produced(a)
            path.write_bytes(made_bytes)
            provenance = Provenance.GENERATED
            scrubbed = []
            yield Event(Stage.ASSETS, "progress",
                        f"{aid} generated"
                        + (" · your logo passed as a reference for the branding "
                           "inside it" if logo_bytes else ""))

            # ASSERT THE BRAND, do not assume the prompt worked. Transcribed
            # across one real project's seven generated assets: four render a
            # brand, two say `voiceowl` and two say `Off-Hook` — and the two that
            # invented it are the hero and the product showcase, the largest
            # images on the page. Naming the product in the prompt makes that
            # much less likely; only reading the image back makes it visible when
            # it happens anyway.
            brand = cur.check_branding(made_bytes, bb.brief.product_name)
            if not brand.ok:
                rejected.append(f"branding not confirmed — {brand.reason()}")
                yield Event(Stage.ASSETS, "blocked",
                            f"{aid}: this image does not show your name. "
                            f"{brand.reason()}. It is kept — a generated surface "
                            f"has no original to fall back to — but upload a real "
                            f"capture for this one if the brand matters here.")

        with Image.open(path) as im:
            w, h = im.size
        made.append(Asset(
            id=aid, section_id=a["section_id"], kind=AssetKind.IMAGE,
            brief=a["brief"],
            prominence=Prominence(a["prominence"]), provenance=provenance,
            path=f"assets/{path.name}", width=w, height=h,
            variants={k: f"assets/{v}" for k, v in derive_variants(path).items()},
            rejected=rejected, scrubbed=scrubbed,
        ))

    if pool is not None:
        pool.shutdown(wait=False)

    bb.assets = made
    rejected = _replace(run, "/assets", [a.model_dump(mode="json") for a in made],
                        agent="curator",
                        summary=f"{len(made)} asset(s) produced — "
                                + ", ".join(f"{m.id}:{m.provenance.value}" for m in made))
    if rejected:
        yield Event(Stage.ASSETS, "blocked",
                    f"assets not recorded ({rejected.code}): {rejected.message}")
    tally = {}
    for m in made:
        tally[m.provenance.value] = tally.get(m.provenance.value, 0) + 1
    skipped = sum(1 for a in plan if a.get("decision") == "skip")
    yield Event(Stage.ASSETS, "done",
                f"{len(made)} asset(s)"
                + (" · " + ", ".join(f"{v} {k}" for k, v in sorted(tally.items())) if tally else "")
                + (f" · {skipped} skipped" if skipped else ""))


def _video_size(path: Path) -> tuple[int, int]:
    """A video's real dimensions, or (0, 0) if they cannot be read."""
    import subprocess

    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
            capture_output=True, text=True, timeout=60).stdout.strip()
        w, h = out.split("x")[:2]
        return int(w), int(h)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0, 0


def _write_png(data: bytes, path: Path, Image) -> None:
    """Normalise whatever the user uploaded to the PNG the workspace expects."""
    import io

    with Image.open(io.BytesIO(data)) as im:
        im.convert("RGB").save(path, "PNG")


def identity_block(run: Run, bb: Blackboard, section: Section) -> str:
    """What the nav and the footer must say the site IS.

    Only for chrome. A content section already has the name in its brief block
    and does not carry the brand mark, so giving it this text would have every
    section drawing a wordmark.

    It exists because the generic line was measurably not enough. `context_block`
    has said "PRODUCT NAME: X — use this exact name everywhere it appears" from
    the beginning, and across eight real projects the nav still came out as
    `<PhoneCall />` from lucide with `aria-label="Platform home"` — a link to the
    home page with no name on it at all. "Everywhere it appears" does not tell a
    builder that the brand entry point is a place it appears; this does.
    """
    if section.id not in CHROME_ORDER:
        return ""

    name = (bb.brief.product_name or "").strip()
    if not name:
        # Unreachable through the API — gate 1 refuses a blank name — but a
        # project created before that gate existed still resumes through here.
        return ""

    lines = [
        "This section is page chrome. It carries the site's identity, and that "
        "is not the blueprint's to decide — the blueprint describes the nav a "
        "SOURCE site has, and a source site's brand is not transferable.",
        "",
        f'REQUIRED: THE BRAND ENTRY POINT READS "{name}".',
        f'It is a link to the top of the page, and the visitor must be able to '
        f'read the name "{name}" from it. A generic icon — a lucide glyph, an '
        f'abbreviation, a coloured square with an initial — is NOT a brand '
        f'entry point. Neither is an aria-label: a screen reader is not the '
        f'only visitor. Set the name as type in the display typeface, at a '
        f'weight and size that make it read as a wordmark rather than as a nav '
        f'link.',
    ]

    logo = bb.logo()
    if logo is None:
        lines += [
            "",
            "There is no logo file — the user chose a wordmark at the material "
            "gate. The name set in type IS the mark. Do not draw a mark to sit "
            "beside it, do not add an icon as a stand-in, and do not put it in "
            "a box to make it look like a logo.",
        ]
    else:
        from sparrow.agents.curator import logo_placement

        src = f"/projects/{run.project_id}/preview/{logo.path}"
        lines += [
            "",
            f"THE USER'S OWN LOGO IS AT `{src}` "
            f"({logo.width}x{logo.height}). Use it in both the nav and the "
            f"footer, beside the name or in place of the name's type if the "
            f"mark already contains the name.",
            "",
            "HARD RULE — THE MARK IS RECOLOURED, NEVER REDRAWN. It is a "
            "trademark. Do not trace it, do not rebuild it out of divs or SVG "
            "paths you write, do not re-letter it in a webfont, do not "
            "substitute an icon that looks like it, and do not stretch it — "
            "constrain one dimension and let the other follow.",
            "",
            logo_placement(run.workspace / "public" / logo.path, bb.design_system),
        ]

    return "<identity>\n" + "\n".join(lines) + "\n</identity>"


def step_build(run: Run) -> Iterator[Event]:
    """Build every section that is not built yet, recording each as it lands.

    RESUME. A section already marked BUILT is skipped rather than rebuilt. That
    is only sound because the status is now written the instant the file is
    written — before this, `status` was `pending` on all nine sections of a
    project whose preview was serving, so skipping on it would have skipped
    nothing and trusting it would have been wrong.

    What that buys, at roughly $0.10-0.25 of builder time per section: a stage
    that died on section six resumes at section six, and `reset_sections` turns
    "just redo the hero" into one section rebuilt rather than the whole page.

    Composition and repair still run on every pass, deliberately. `page.tsx` has
    to name every section including the ones this pass skipped, and a workspace
    that does not build is not a thing to hand to VERIFY — that is what took two
    whole experiments to notice the first time.
    """
    from sparrow.agents.builder import Builder, write_section
    from sparrow.blueprints import load_dir

    bb = _bb(run)
    content = load_content(run)
    blueprints = load_dir(run.dir / "blueprints")
    ws = run.workspace
    primitives = sorted(p.stem for p in (ws / "src/components/ui").glob("*.tsx"))
    builder = Builder()
    # The winning source per section, from scout. builder's prompt has asked for
    # this since 6398b98; the arguments were never passed, so every build raised
    # NameError on the first section. Loaded once, not per section.
    winners = load_winners(run)
    # Built once for the whole stage, not per section — it is the same image
    # nine times over, and re-tiling it each round is pure latency.
    sheet = _page_sheet(run)
    from sparrow.agents.reader import to_block

    observed = to_block(load_reading(run))
    built = skipped = 0

    for section in sorted(bb.sections, key=lambda s: s.order):
        bp = blueprints.get(section.blueprint_id)
        if bp is None:
            continue
        # BUILT plus a file on disk. The status alone would resume a run whose
        # workspace was rebuilt from the scaffold into composing a page.tsx that
        # imports components no longer there, which fails the build with an error
        # about a missing module and says nothing about why.
        if section.status is BuildStatus.BUILT and (ws / section.target_path).exists():
            skipped += 1
            yield Event(Stage.BUILD, "progress",
                        f"{section.id}: already built — kept")
            continue

        out = builder.build(bb, section, bp, stack=STACK,
                            available_primitives=primitives,
                            # The logo is EXCLUDED here and passed through
                            # `identity` instead. The <assets> block carries the
                            # prominence rules — "a dominant asset is at least
                            # 60% of the section's height" — which are written
                            # for content imagery. Those firing on a nav asset
                            # is precisely what produced the full-width blank
                            # box above the hero.
                            assets=[a for a in bb.assets_for(section.id)
                                    if a.kind is not AssetKind.LOGO],
                            asset_base=f"/projects/{run.project_id}/preview",
                            copy=(content.get(section.id) or {}).get("slots"),
                            carried_elsewhere=[
                                str(v) for sid_, e in content.items() if sid_ != section.id
                                for k, v in (e.get("slots") or {}).items()
                                if (e.get("provenance") or {}).get(k) == "user_supplied"
                                and isinstance(v, str) and v.strip()],
                            identity=identity_block(run, bb, section),
                            source_shot=_b64(
                                (winners.get(section.id) or {}).get("shot")),
                            source_html=_source_markup(
                                (winners.get(section.id) or {}).get("html")),
                            page_shot=sheet,
                            composition=composition_block(
                                bb, section, load_winners(run).get(section.id)),
                            observed=observed)
        write_section(ws, section, out.code,
                      asset_base=f"/projects/{run.project_id}/preview")
        # Immediately, per section. The file and the record of the file are one
        # transition; anything between them is a window in which a crash leaves
        # the blackboard lying about the workspace.
        rejected = _record_section(run, section.id, agent="builder",
                                   status=BuildStatus.BUILT, bump_attempt=True,
                                   defects=[],
                                   note=f"{len(out.code.splitlines())} loc")
        if rejected:
            yield Event(Stage.BUILD, "blocked",
                        f"{section.id} built but not recorded ({rejected.code}): "
                        f"{rejected.message}")
        built += 1
        yield Event(Stage.BUILD, "progress",
                    f"{section.id}: {len(out.code.splitlines())} loc",
                    cost=out.usage.cost(builder.provider.name, builder.tier))

    from sparrow.cli import _compose_page, _repair_until_builds
    _compose_page(bb, ws)
    ok, spent = _repair_until_builds(bb, ws, builder.provider.name)
    run.spent += spent
    kept = (f" · {built} built, {skipped} kept from a previous run"
            if skipped else "")
    if not ok:
        # Raised, not yielded as a warning. VERIFY's first act is to shoot the
        # static export, so a run that carries on from here fails there instead
        # — reporting "no static export at workspace/out", which describes the
        # consequence and names neither the file nor the error that caused it.
        raise RuntimeError(
            "the section files were written but the workspace does not compile "
            "— see the build output above for the failing file" + kept)
    yield Event(Stage.BUILD, "done", "page composed and built" + kept)


class AssetsNotServed(RuntimeError):
    """The page's own requests 404'd, so nothing rendered on it is real.

    Worth its own type because the response is different from every other
    finding: there is nothing to fix in a section file, and no judgement to
    make about a page that never loaded its stylesheet. A capture taken in
    this state shows Times New Roman on white with every Motion section frozen
    at its initial opacity — and the inspector, honestly, reports collisions
    and faded text. The fixer then reads a source file that is completely
    fine, disputes, and the loop burns all three rounds arguing about a
    screenshot of a page nobody will ever see.

    Measured on a real export after previews moved to Next's `basePath`: 24
    failed requests, no stylesheet, no JS. That was a bug in how the export was
    served (`capture.base_path`), and it cost three paid rounds before anyone
    looked at a crop. `failed_requests` was already being collected and nothing
    read it. This is that check, and it is free.
    """

    def __init__(self, urls: list[str]) -> None:
        self.urls = urls
        super().__init__(
            f"{len(urls)} request(s) failed while loading the page, so it did not "
            "render as a visitor would see it and there is nothing worth "
            "inspecting: " + ", ".join(urls[:5])
            + (f" (+{len(urls) - 5} more)" if len(urls) > 5 else "")
        )


# Extensions whose absence changes what the page IS, versus what it SHOWS.
_RENDER_CRITICAL = (".css", ".js", ".mjs")


def _blocks_rendering(url: str) -> bool:
    """Did this failure stop the page rendering, or just leave a hole in it?

    `AssetsNotServed` exists for the first case — an export served without its
    stylesheet renders Times New Roman on white with every Motion section frozen,
    and inspecting that burns paid rounds arguing about a screenshot nobody will
    see. It is the wrong response to the second case: a page that rendered
    correctly and is missing one image has plenty worth inspecting, and the
    missing image is a defect a fixer can actually repair.

    Measured on meridian-v2: five 404s, all <img>, on a page whose CSS and JS
    loaded fine. Halting there would report "nothing worth inspecting" about a
    page that was almost entirely right.
    """
    path = url.split("?")[0].rstrip("/")
    tail = path.rsplit("/", 1)[-1]
    if any(path.endswith(x) for x in _RENDER_CRITICAL):
        return True
    return "." not in tail          # the document itself


def _inspect_once(run: Run, bb, blueprints, port: int = 4600,
                  disputed: dict[str, list[str]] | None = None,
                  only: set[str] | None = None):
    """One full look at the built page. Returns (page_findings, per_section, cost).

    Raises `AssetsNotServed` BEFORE the first model call if the page could not
    load its own assets. Everything below this line costs money per section.
    """
    from sparrow.agents.inspector import Defect, Inspector, deterministic_defects
    from sparrow.capture import inspect_page, serve

    out = run.workspace / "out"
    if not (out / "index.html").exists():
        raise RuntimeError(
            "no static export at workspace/out — the build did not complete, so "
            "there is nothing to verify. Check the build stage."
        )
    with serve(out, port=port) as url:
        reports = inspect_page(url, run.dir / "shots" / "sections")

    failed = sorted({u for r in reports.values() for u in r.failed_requests})
    # Only the failures that stopped the page rendering abort the inspection.
    # The rest — a 404 image, a missing poster — stay in `failed_requests` and
    # come out of `deterministic_defects` below as `request-failed` defects,
    # attached to the section that referenced them, where the fixer can act.
    blocking = [u for u in failed if _blocks_rendering(u.split(" ", 1)[-1])]
    if blocking:
        raise AssetsNotServed(blocking)

    page_level = deterministic_defects(reports)

    by_index: dict[int, list] = {}
    for r in reports.values():
        for sh in r.sections:
            by_index.setdefault(sh.section_index, []).append(sh)

    inspector = Inspector()
    ordered = sorted(bb.sections, key=lambda s: s.order)
    per_section: dict[str, list] = {}
    cost = 0.0
    # DENSITY, computed and free, over every section. The built section is
    # measured the way the source band was; the range it is held to is the
    # sources' own span for that section type. Below the floor is a band with
    # air inside it — the thing that reads as unfinished and that no model
    # judge has ever reported, because a sparse band is not "wrong", only less.
    dens_src = load_density(run)
    winners_ = load_winners(run)
    built = {d["index"]: d for r in reports.values() for d in (r.density or [])}
    for pos, idx in enumerate(sorted(by_index)):
        if pos >= len(ordered):
            break
        sec = ordered[pos]
        if only is not None and sec.id not in only:
            continue
        d = built.get(idx)
        rng = density_range(dens_src, sec.blueprint_id) if dens_src else None
        if d and rng and d.get("words_per_k") is not None and d["words"] >= 8:
            lo, hi = rng
            own = ((winners_.get(sec.id) or {}).get("density") or {}).get("words_per_k")
            if d["words_per_k"] < lo or d["words_per_k"] > hi:
                side = "sparser" if d["words_per_k"] < lo else "denser"
                per_section.setdefault(sec.id, []).append(Defect(
                    severity="medium", code="density-outside-source-range",
                    what=(f"this section carries {d['words_per_k']} words per 1000px "
                          f"over {d['height']}px; the sources span {lo}–{hi} for a "
                          f"{sec.blueprint_id}"
                          + (f" and the band this one was built from carries {own}" if own else "")
                          + f" — it is {side} than any of them. "
                          + ("Height is a consequence of content: cut the vertical "
                             "padding and min-height that hold air, and let the band be "
                             "as tall as what it carries." if side == "sparser" else
                             "Give it the room the source gives the same content.")),
                    where=f"{sec.target_path}", source="computed"))
        # ONLY WHAT CHANGED. A section the fixer did not write is byte-identical
        # to the last time it was judged, and judging it again buys one thing:
        # a different answer. Measured: findings went 1 → 12 → 1 → 4 → 9 across
        # rounds on a page where the fixer touched two or three sections per
        # round — the other four or five were being re-read by a nondeterministic
        # judge and coming back with fresh opinions. The page-level checks above
        # are deterministic and free and still run over everything; the model
        # is asked only about files that moved.
        defects, usage = inspector.inspect_section(
            bb, sec, by_index[idx], page_level, blueprints.get(sec.blueprint_id),
            (disputed or {}).get(sec.id))
        cost += usage.cost(inspector.provider.name, inspector.tier)
        if defects:
            per_section.setdefault(sec.id, []).extend(defects)
    return page_level, per_section, cost


_ASSET_REF = re.compile(r"assets/[A-Za-z0-9._-]+")


def _assets_lost(before: str, after: str) -> list[str]:
    """Which images the section used to render and no longer does."""
    return sorted(set(_ASSET_REF.findall(before)) - set(_ASSET_REF.findall(after)))


def _drift_defects(findings: list, bb: Blackboard) -> dict[str, list]:
    """Group audit findings by the section whose file they were measured in.

    `audit.Finding` and inspector `Defect` are deliberately different shapes —
    one is a line in a file, the other is something seen in a browser — so this
    adapts rather than pretending they are one type. What has to survive the
    adaptation is what `Fixer.fix` actually reads (`severity`, `what`, `where`)
    plus `source`, which is how a person reading the log tells a measured
    finding from a judged one.

    Severity is one value for every category, not a ranking. Drift is a
    consistency violation, never a rendering break, and deciding that an
    off-scale radius outranks an off-scale gap would be exactly the unmeasured
    preference §6 rejects. The fixer is told what is wrong and what the scale
    permits; it is not told which drift to care about most.

    The permitted set travels WITH the finding, quoted from the same
    `DesignSystem` the audit derived it from. Without it the fixer knows only
    that gap-7 is wrong, and a fixer guessing at the remedy replaces one
    off-scale value with another.
    """
    from sparrow.agents.inspector import Defect
    from sparrow.audit import permitted

    owner = {Path(s.target_path).name: s.id for s in bb.sections}
    allow = permitted(bb.design_system)
    out: dict[str, list] = {}
    for f in findings:
        sid = owner.get(f.file)
        if sid is None:
            # A .tsx no section owns. It is still reported in the count at the
            # gate; there is simply no section to route a fix to.
            continue
        what = f"{f.category}: {f.detail}"
        ok = allow.get(f.category)
        if ok:
            what += f" — the design system declares only {', '.join(sorted(ok))}"
        out.setdefault(sid, []).append(Defect(
            severity="medium", code=f.category, what=what,
            where=f"{f.file}:{f.line}", source="computed",
        ))
    return out


def _settle_sections(run: Run, bb: Blackboard, findings: list,
                     per_section: dict[str, list],
                     disputed: dict[str, list[str]]) -> Iterator[Event]:
    """Write the last look's verdict onto every section that was built.

    Both halves count. Drift is measured from the code and visual defects are
    seen in a browser, and a section carrying either is not clean — the gate
    question already reports both, and a `status` that disagreed with the
    sentence next to it would be worse than no status.

    PENDING sections are left alone. A section with no blueprint is never built
    and never inspected, and marking it BUILT here because the inspector had
    nothing to say about it would invent a build that did not happen — which is
    the same class of lie, pointing the other way, as the one this work fixes.
    """
    remaining = _drift_defects(findings, bb)
    for sid, ds in per_section.items():
        remaining.setdefault(sid, []).extend(ds)

    for section in bb.sections:
        if section.status is BuildStatus.PENDING:
            continue
        ds = remaining.get(section.id, [])
        note = ""
        if not ds and disputed.get(section.id):
            # Clean, but only after the fixer refused some of what it was shown.
            # Worth a line: the difference between "nothing was wrong" and
            # "something was reported and argued down" is the whole diagnosis.
            note = f"clean, {len(disputed[section.id])} defect(s) disputed"
        rejected = _record_section(
            run, section.id, agent="observer",
            status=BuildStatus.DEFECTIVE if ds else BuildStatus.BUILT,
            defects=[f"{d.source}:{d.code} {d.what}" for d in ds], note=note)
        if rejected:
            yield Event(Stage.VERIFY, "blocked",
                        f"{section.id} verdict not recorded ({rejected.code}): "
                        f"{rejected.message}")


def step_verify(run: Run) -> Iterator[Event]:
    """Look, fix, look again — until the page is clean or the budget is spent.

    Until now this stage inspected the page, counted the defects, and threw them
    away: `total += len(defects)` and nothing more. Gate 3 then asked "ship it?"
    while holding a list of problems nothing could act on, and the harness was
    paying about $1.20 a run for findings it discarded.

    That is the missing half of CLAUDE.md §6's build → look → fix loop. Capped at
    3 like every other loop, because critic-refine plateaus at two or three
    iterations and then starts inventing objections to justify itself.

    The DRIFT half stayed discarded after the visual half was wired up.
    `audit_dir` ran at the top of every round and its findings reached the
    progress line and the gate question — but only `per_section` was passed to
    the fixer, so nothing ever acted on them. A real run reported 31
    off-scale-gap findings in round one, again in round two, and again at the
    gate, and fixed none of them. Drift now goes to the fixer alongside what the
    inspector saw, in ONE call per section: two calls would have the second
    fixing code the first had already rewritten.
    """
    from sparrow.agents.builder import Fixer, write_section
    from sparrow.audit import audit_dir, summarise
    from sparrow.blueprints import load_dir
    from sparrow.cli import _run_build
    from sparrow.loop import Blocked, Outcome, Rounds

    bb = _bb(run)

    # SPARROW_SKIP_VERIFY=1 goes straight to the preview gate with the page as
    # built. Verify is the slowest and most expensive stage — 21+ model calls
    # and three full rebuilds on a 7-section page — and the person deciding
    # whether that spend is worth it is the one looking at the page. Nothing is
    # settled: sections stay BUILT, no verdict is invented, and the gate says
    # plainly that no one has looked. A later /advance with the flag off runs
    # verify normally from here.
    if os.environ.get("SPARROW_SKIP_VERIFY", "").strip() in ("1", "true", "yes"):
        raise Halt(GateRequest(
            Stage.GATE_PREVIEW,
            "The site is built. Verify was SKIPPED (SPARROW_SKIP_VERIFY) — nothing "
            "has inspected the rendered page. Ship it, or unset the flag and "
            "advance again to verify?",
            options=[{"choice": "approve", "label": "Looks good — publish"},
                     {"choice": "revise", "label": "Send it back with a note",
                      "needs_note": True}],
            artifacts=[str(run.workspace / "out")],
        ))

    blueprints = load_dir(run.dir / "blueprints")
    rounds = Rounds("verify", cap=3)
    # The count lived in this object and this object lives for one call, so a
    # restart mid-verify began again at 0/3 — the cap in CLAUDE.md §8 was a cap
    # per process, not per page. Persisted after every round; cleared when the
    # stage reaches its gate, so the next verify the user asks for is a new one.
    rounds_path = run.dir / "verify-rounds.json"
    try:
        rounds.spent = int(json.loads(rounds_path.read_text()).get("spent", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    if rounds.spent:
        yield Event(Stage.VERIFY, "progress",
                    f"resuming verify at {rounds.spent}/{rounds.cap} attempts spent")

    def _persist_rounds() -> None:
        rounds_path.write_text(json.dumps({"spent": rounds.spent}))

    fixer: Fixer | None = None
    unserved: list[str] = []
    # A disputed defect must not come back next round. Without this the inspector
    # re-reports it, the fixer disputes it again, and the loop spends its whole
    # budget on one thing nobody is going to change.
    disputed: dict[str, list[str]] = {}
    port = 4600
    # Verdicts carried between rounds. `None` on the first pass means "look at
    # everything"; after that, only the sections the fixer wrote are looked at
    # again and every other section keeps the verdict it already has.
    touched: set[str] | None = None
    verdicts: dict[str, list] = {}

    while True:
        findings = audit_dir(run.workspace / "src/components/sections", bb.design_system,
                             load_winners(run),
                             {s.id: Path(s.target_path).name for s in bb.sections})
        try:
            page_level, fresh, cost = _inspect_once(run, bb, blueprints, port,
                                                    disputed, only=touched)
        except AssetsNotServed as e:
            # Stop the round before the inspector is asked anything. Nothing in a
            # section file explains a 404, so every model call this round would
            # buy an opinion about a page that never loaded.
            yield Event(Stage.VERIFY, "blocked",
                        f"the preview is not serving its own assets — {e}")
            unserved = e.urls
            break
        port += 1                       # a fresh port each pass; the last may still be closing
        # Merge: a re-inspected section's verdict is replaced (cleared if it came
        # back with nothing); an untouched one keeps its last verdict.
        for sid in (touched if touched is not None else [s.id for s in bb.sections]):
            verdicts.pop(sid, None)
        verdicts.update(fresh)
        per_section = dict(verdicts)

        # Drift is NOT suppressed by `disputed` the way a visual defect is.
        # There is nothing to dispute about arithmetic against a closed scale,
        # so it is recomputed from the code every round and stays on the list
        # until the code stops drifting.
        drift = _drift_defects(findings, bb)
        work: dict[str, list] = {}
        for sid in (*drift, *per_section):
            # Drift first: it names a file and a line, which orients the fixer
            # before it reads a description of something merely seen.
            work.setdefault(sid, [*drift.get(sid, []), *per_section.get(sid, [])])

        remaining = sum(len(v) for v in per_section.values())
        yield Event(Stage.VERIFY, "progress",
                    f"{summarise(findings).splitlines()[0]} · "
                    f"{len(page_level)} computed · {remaining} visual", cost=cost)

        if not work:
            rounds.complete("audit clean and no visual defects")
            break

        slot = rounds.reserve()
        if isinstance(slot, Blocked):
            yield Event(Stage.VERIFY, "blocked", f"{slot.code}: {slot.message}")
            break

        # Recorded BEFORE the first fixer call of the round. The fixer is the
        # part that can throw, time out, or be killed; a defect list that only
        # lands after it returns is a defect list that is absent exactly when
        # someone needs to know what the run was working on when it died.
        # `_record_section` writes nothing when nothing moved, so a second round
        # that finds the same defects does not churn the version.
        for sid, defects in work.items():
            rejected = _record_section(
                run, sid, agent="inspector", status=BuildStatus.DEFECTIVE,
                defects=[f"{d.source}:{d.code} {d.what}" for d in defects])
            if rejected:
                yield Event(Stage.VERIFY, "blocked",
                            f"{sid} defects not recorded ({rejected.code}): "
                            f"{rejected.message}")

        fixer = fixer or Fixer()
        fixed_any = False
        errored = 0
        touched = set()
        # Every file this round is about to overwrite, as it stood before the
        # overwrite. This is what a failed rebuild is restored from.
        snapshots: dict[Path, str] = {}
        for sid, defects in work.items():
            section = next(s for s in bb.sections if s.id == sid)
            path = run.workspace / section.target_path
            before = path.read_text()
            try:
                out, dispute = fixer.fix(bb, section, before, defects)
            except Exception as e:
                errored += 1
                yield Event(Stage.VERIFY, "blocked", f"{sid}: fixer failed — {e}")
                continue
            if dispute:
                disputed.setdefault(sid, []).append(dispute)
                # A disputed section is not rewritten, so it is not re-inspected;
                # its carried verdict has to go with the dispute or the same
                # defects re-enter `work` every round from memory.
                verdicts.pop(sid, None)
                # THE reason this stage got a writer. A dispute changes no field
                # on the blackboard, suppresses the defect for every later round,
                # and until now lived only in the `disputed` dict above — which
                # dies with the process. One run spent three rounds and ~$2 on
                # four disputes and afterwards there was nothing on disk saying
                # what had been disputed, so nothing to diagnose. It is the
                # fixer's own prose about a section file, not user material.
                rejected = _note(run, agent="fixer",
                                 summary=f"{sid}: DISPUTED — {dispute}")
                if rejected:
                    yield Event(Stage.VERIFY, "blocked",
                                f"{sid} dispute not recorded ({rejected.code}): "
                                f"{rejected.message}")
                yield Event(Stage.VERIFY, "progress", f"{sid}: disputed — {dispute[:70]}")
                continue
            # A fix may not throw away imagery. Measured on the voice-ai run:
            # the fixer repaired three defects in integration-grid and one in
            # feature-grid, and in doing so removed the <Image> for
            # integration-grid-1 and feature-grid-1 — both of them the user's
            # OWN uploaded files, still on disk and on the blackboard, referenced
            # by nothing. The section rendered without them and no check noticed,
            # so the repair loop quietly deleted the one thing §2 calls the
            # differentiator. Dropping an asset is never the fix for a visual
            # defect; if the layout cannot hold the image, that is an escalation,
            # not a deletion.
            lost = _assets_lost(before, out.code)
            if lost:
                yield Event(Stage.VERIFY, "blocked",
                            f"{sid}: fix rejected — it removed {', '.join(lost)}, "
                            "which the section is built to show")
                continue
            snapshots.setdefault(path, before)
            write_section(run.workspace, section, out.code,
                          asset_base=f"/projects/{run.project_id}/preview")
            touched.add(sid)
            # Status stays DEFECTIVE. The file changed; nothing has looked at the
            # result yet, and loop.py's fourth rule is that nothing is marked done
            # on an agent's say-so. The next round's inspection is the evidence,
            # and the settle at the end of the stage is where it is applied.
            rejected = _record_section(
                run, sid, agent="fixer", bump_attempt=True,
                note="fix applied for " + ", ".join(sorted({d.code for d in defects})))
            if rejected:
                yield Event(Stage.VERIFY, "blocked",
                            f"{sid} fix not recorded ({rejected.code}): "
                            f"{rejected.message}")
            fixed_any = True
            yield Event(Stage.VERIFY, "progress",
                        f"{sid}: fixed {len(defects)} defect(s)",
                        cost=out.usage.cost(fixer.provider.name, fixer.tier))

        if not fixed_any:
            if errored and errored >= len(work) - sum(len(v) for v in disputed.values()):
                # Nothing was fixed because the FIXER COULD NOT BE REACHED, not
                # because it disagreed. Measured: eight consecutive
                # APIConnectionErrors during a seven-minute Azure outage were
                # reported as "every defect was disputed", the round was settled
                # as superseded, and the gate opened claiming the fixer had
                # argued its case. An outage is not an argument.
                rounds.settle(Outcome.ATTEMPTED, f"{errored} fixer call(s) failed")
                _persist_rounds()
                yield Event(Stage.VERIFY, "blocked",
                            f"nothing changed — {errored} fixer call(s) failed to "
                            f"reach the model. This round is not evidence of anything; "
                            f"advance again when the provider is reachable.")
                break
            # Every defect was disputed, so another pass would look at the same
            # page and find the same things. Stop rather than burn the budget.
            rounds.settle(Outcome.SUPERSEDED, "all defects disputed")
            _persist_rounds()
            yield Event(Stage.VERIFY, "progress",
                        "nothing changed — every defect was disputed")
            break

        rounds.settle(Outcome.ATTEMPTED,
                      f"fixed {sum(len(v) for v in work.values())} defect(s)")
        _persist_rounds()
        ok, output = _run_build(run.workspace)
        if not ok:
            # This branch used to emit "reverting to the last good export" and
            # break, having restored nothing. The workspace was left holding the
            # code that had just failed to build, behind a message claiming
            # recovery — one project sat unbuildable for hours that way. The
            # sentence is now the thing that happens.
            reverted = []
            for target, original in snapshots.items():
                target.write_text(original)
                sid = next((x.id for x in bb.sections
                            if run.workspace / x.target_path == target), None)
                if sid:
                    reverted.append(sid)
                    _record_section(run, sid, agent="orchestrator",
                                    status=BuildStatus.DEFECTIVE,
                                    note="fix reverted — it did not build")
            recovered, again = _run_build(run.workspace)
            if not recovered:
                # Nothing further in this stage can help, and gate 3 must not
                # ask a human to ship a workspace that does not compile.
                raise RuntimeError(
                    "a fix broke the build and restoring the previous section "
                    "code did not recover it — the workspace does not build. "
                    "This needs a look, not another round.\n"
                    + again.strip()[-1200:]
                )
            yield Event(Stage.VERIFY, "blocked",
                        f"a fix broke the build — reverted {len(snapshots)} "
                        "section(s) to the last code that built, and rebuilt")
            break
        yield Event(Stage.VERIFY, "progress", f"rebuilt · {rounds.summary()}")

    findings = audit_dir(run.workspace / "src/components/sections", bb.design_system,
                             load_winners(run),
                             {s.id: Path(s.target_path).name for s in bb.sections})
    looked = True
    try:
        _, fresh, _ = _inspect_once(run, bb, blueprints, port + 10, disputed,
                                    only=touched)
        for sid in (touched if touched is not None else [s.id for s in bb.sections]):
            verdicts.pop(sid, None)
        verdicts.update(fresh)
        per_section = dict(verdicts)
        left = sum(len(v) for v in per_section.values())
    except AssetsNotServed as e:
        per_section, left, unserved, looked = {}, 0, e.urls, False

    # One settle, on the evidence of the last look. A section is BUILT again only
    # because something measured it clean — never because a fix was written and
    # assumed to have worked. If the final look never happened (the page could
    # not serve its own files) nothing is settled at all: the alternative is
    # marking every section clean on the strength of an inspection that returned
    # no defects because it never ran.
    if looked:
        for ev in _settle_sections(run, bb, findings, per_section, disputed):
            yield ev

    # A page that cannot load its own assets is not a page anyone should be asked
    # to ship, so that leads the question rather than sitting in a log line.
    headline = (
        f"The preview is not serving {len(unserved)} of its own files, so what "
        "you see is unstyled and is not what was built. This needs fixing before "
        "it can be judged. "
        if unserved else "The site is built. "
    )
    rounds_path.unlink(missing_ok=True)
    raise Halt(GateRequest(
        Stage.GATE_PREVIEW,
        headline
        + f"{len(findings)} drift finding(s), {left} visual defect(s)"
        + (f", {sum(len(v) for v in disputed.values())} disputed" if disputed else "")
        + f". {rounds.summary()}. Ship it?",
        options=[{"choice": "approve", "label": "Looks good — publish"},
                 {"choice": "revise", "label": "Send it back with a note",
                  "needs_note": True}],
        artifacts=[str(run.workspace / "out")],
    ))


def preview_base(run: Run) -> str:
    return f"/projects/{run.project_id}/preview"


def preview_bound(run: Run) -> bool:
    """Is the export on disk built for the path the preview serves it from?

    Two things have to agree and they drift independently. `next.config.ts`
    carries `basePath`, which Next uses for its own `_next/…` URLs. The section
    sources carry the prefix on every `/assets/…` src, because `next/image` with
    `unoptimized` does NOT prepend basePath and never has.

    A Cloudflare deploy rewrote both — config and every section file — back to
    root-relative, twice, and each time the preview came back as a page whose
    stylesheets loaded and whose images all 404'd. Nothing detected it; it just
    looked broken.
    """
    from sparrow.capture import base_path

    out = run.workspace / "out"
    if not (out / "index.html").is_file():
        return True                      # nothing built yet is not "unbound"
    if base_path(out) != preview_base(run):
        return False

    # And the asset srcs, which the config does NOT govern. The first version of
    # this checked only `base_path`, which reads the `_next/` prefix — that comes
    # from next.config.ts. It reported the ide project as bound while every one
    # of its images was root-relative and 404ing, because Next prefixes its own
    # chunks and leaves an unoptimized <Image> src exactly as written.
    #
    # Read from the EXPORT rather than the sources: the export is what is served,
    # and it is the only place both halves have been resolved.
    html = "\n".join(f.read_text(errors="ignore")
                     for f in out.rglob("*.html"))
    return '"/assets/' not in html and "'/assets/" not in html


def rebind_preview(run: Run) -> dict:
    """Put the preview binding back on the config and every asset src.

    Returns what changed. Does NOT rebuild — the caller decides, because a
    rebuild is slow and a caller that only wanted to know can ask `preview_bound`.
    """
    from sparrow.agents.builder import prefix_assets

    base = preview_base(run)
    changed: dict = {"config": False, "sections": []}

    cfg = run.workspace / "next.config.ts"
    if cfg.is_file() and "basePath" not in cfg.read_text():
        cfg.write_text(cfg.read_text().replace(
            "  trailingSlash: true,",
            f'  trailingSlash: true,\n\n'
            f'  // Bound to the preview path so Next generates correct URLs in the\n'
            f'  // HTML, the RSC payload and at runtime. Without it hydration fails\n'
            f'  // silently and nothing animates.\n'
            f'  basePath: "{base}",\n'
            f'  assetPrefix: "{base}",'))
        changed["config"] = True

    secs = run.workspace / "src/components/sections"
    for f in sorted(secs.glob("*.tsx")) if secs.is_dir() else []:
        before = f.read_text()
        after = prefix_assets(before, base)
        if after != before:
            f.write_text(after)
            changed["sections"].append(f.name)
    return changed


def make_workspace(run: Run, scaffold: Path) -> None:
    """Copy the scaffold and bind it to the path the preview serves from.

    Rewriting root-absolute URLs in the served HTML is not enough for a Next app.
    Its RSC payload carries "/_next/static/chunks/..." inside JSON strings, and
    its client runtime builds more paths at runtime — none of which an HTML
    rewrite can reach. The scripts then load but the module registry does not
    match, hydration fails silently with no console error and no 404, and every
    element stays frozen at its `initial` opacity. Which is what "the page is
    invisible and there is no animation" turned out to be.

    basePath makes Next generate correct URLs everywhere itself. The export is
    then bound to this project's preview path, which is what a preview is for.
    """
    ws = run.workspace
    ws.mkdir(parents=True, exist_ok=True)
    shutil.copytree(scaffold, ws, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", ".next", "out", "README.md"))
    cfg = ws / "next.config.ts"
    base = f"/projects/{run.project_id}/preview"
    cfg.write_text(cfg.read_text().replace(
        "  trailingSlash: true,",
        f'  trailingSlash: true,\n\n'
        f'  // Bound to the preview path so Next generates correct URLs in the\n'
        f'  // HTML, the RSC payload and at runtime. Without it hydration fails\n'
        f'  // silently and nothing animates.\n'
        f'  basePath: "{base}",\n'
        f'  assetPrefix: "{base}",'))
    subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=ws, check=True,
                   capture_output=True)

"""dsh-builder-01: does Sparrow need its own builder, or only its brain?

Same brief, same sources, same owner material (voiceowl), three ways:

  A  Sparrow end to end — the original pipeline output, untouched in the office.
  B  DeepSeek Harness from a prompt + the sources — what "just give it to an
     agent" means: build rules, source screenshots, the owner's uploads, and a
     request written the way a user would type it. No Sparrow decisions.
  C  Sparrow's brain + DeepSeek's hands — the blackboard's decisions (tokens,
     fonts, curated assets, and per section: blueprint, composition, identity,
     verbatim copy, assets, the winning source band) handed to the same agent,
     with the builder's sections removed.

B and C run through the identical studio loop (edit → build → look → one
checkpoint) on the same model, so the only variable is what the agent is given.

    uv run --extra workshop python ../experiments/dsh-builder-01/run.py setup b
    uv run --extra workshop python ../experiments/dsh-builder-01/run.py run b
    uv run --extra workshop python ../experiments/dsh-builder-01/run.py measure a
"""

from __future__ import annotations

import base64
import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend" / "src"))

from sparrow import api, dossier, gateway, steps  # noqa: E402  (loads backend/.env)
from sparrow.blackboard.schema import AssetKind, Blackboard  # noqa: E402
from sparrow.workshop import look, store  # noqa: E402
from sparrow.workshop.config import WorkshopConfig  # noqa: E402

import os  # noqa: E402

# Which project's brain to test, and the prefix for the experiment workspaces.
# Defaults reproduce the first run (voiceowl → exp-b, exp-c).
SRC = os.environ.get("EXP_SRC", "voiceowl")
PROJ = ROOT / "projects" / SRC
_PREFIX = os.environ.get("EXP_PREFIX", "exp")
PIDS = {"b": f"{_PREFIX}-b", "c": f"{_PREFIX}-c", "c2": f"{_PREFIX}-c2",
        "cplus": f"{_PREFIX}-cplus", "bplus": f"{_PREFIX}-bplus"}
OUT = HERE / os.environ.get("EXP_OUT", ".")
OUT.mkdir(parents=True, exist_ok=True)


def _bb() -> Blackboard:
    return Blackboard.model_validate_json((PROJ / "blackboard.json").read_text())


def _scaffold_copy(dest: Path, pid: str) -> None:
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(ROOT / "scaffold", dest,
                    ignore=shutil.ignore_patterns("node_modules", ".next", "out", "README.md"))
    cfg = dest / "next.config.ts"
    base = f"/projects/{pid}/preview"
    cfg.write_text(cfg.read_text().replace(
        "  trailingSlash: true,",
        f'  trailingSlash: true,\n  basePath: "{base}",\n  assetPrefix: "{base}",'))


def _stack_rules(base: str) -> str:
    """The build rules every variant needs to produce a working export — and nothing
    about the site itself. Cut from the dossier so B and C get identical rules."""
    full = dossier.render(Blackboard(project_id="x"), {}, base)
    return full[full.index("## Build rules"):]


# ── setup ───────────────────────────────────────────────────────────────────

def setup_b(stage: Path, pid: str) -> str:
    _scaffold_copy(stage, pid)
    refs = stage / "refs"
    refs.mkdir()
    for f in sorted((PROJ / "sources").glob("*.png")):
        if re.search(r"-(b\d+|sheet)\.png$", f.name):
            shutil.copy(f, refs / f.name)
    up = stage / "public" / "assets" / "uploads"
    up.mkdir(parents=True)
    for f in sorted((PROJ / "uploads").iterdir()):
        if "--scrubbed" not in f.name:
            shutil.copy(f, up / f.name)
    base = f"/projects/{pid}/preview"
    return ("# Workspace\n\nA Next.js + Tailwind + shadcn scaffold, not yet built into a site.\n\n"
            "- `refs/` holds screenshots of the reference sites, cut into bands top to bottom "
            "(`<site>-b00.png` is the top), plus a `<site>-sheet.png` overview of each. View "
            "them with read_image.\n"
            "- `public/assets/uploads/` holds the owner's real files.\n\n" + _stack_rules(base))


def build_plan(bb: Blackboard, run, pid: str) -> str:
    """Sparrow's per-section decisions, assembled the way step_build assembles them."""
    content = steps.load_content(run)
    winners = steps.load_winners(run)
    base = f"/projects/{pid}/preview"
    blueprints = {p.stem.split("-", 1)[1]: p.read_text() for p in (PROJ / "blueprints").glob("*.md")}
    out = ["# Build plan",
           "",
           "The site is not built yet. Build every section below, in this order, each as its "
           "own component at the file named, then compose them in `src/app/page.tsx` in the "
           "same order. The design tokens and fonts are already in `src/app/globals.css` and "
           "`src/app/layout.tsx`; the curated images and videos are in `public/assets/`. Each "
           "section names the source band it is modelled on (`refs/<section>.png`): view it "
           "with read_image before building the section and match its structure, rhythm and "
           "density — not its brand, colours or words.",
           ""]
    for s in sorted(bb.sections, key=lambda s: s.order):
        out += [f"## {s.order}. `{s.id}` → `{s.target_path}` (component `{s.component_name}`)", ""]
        if s.id in blueprints:
            out += [blueprints[s.id].split("\n", 1)[1].strip(), ""]
        out += ["### Composition", "", steps.composition_block(bb, s, winners.get(s.id)), ""]
        ident = steps.identity_block(run, bb, s)
        if ident.strip():
            out += ["### Identity", "", ident.strip(), ""]
        slots = (content.get(s.id) or {}).get("slots") or {}
        if slots:
            out += ["### Copy — verbatim, and nothing beyond it", ""]
            for k, v in slots.items():
                out.append(f"- {k}: " + (" | ".join(map(str, v)) if isinstance(v, list) else str(v)))
            out.append("")
        assets = [a for a in bb.assets_for(s.id) if a.kind is not AssetKind.LOGO]
        logo = bb.logo()
        if s.id in ("nav", "footer") and logo:
            assets.append(logo)
        if assets:
            out += ["### Assets", ""]
            for a in assets:
                variants = ", ".join(f"{k}: `{base}/{v}`" for k, v in a.variants.items())
                out.append(f"- `{base}/{a.path}` ({a.kind.value}, {a.prominence.value}, "
                           f"{a.provenance.value}) — {a.brief[:200]}"
                           + (f" · variants: {variants}" if variants else ""))
            out.append("")
        if (winners.get(s.id) or {}).get("shot"):
            out += [f"Reference band: `refs/{s.id}.png` ({winners[s.id].get('site')})", ""]
    return "\n".join(out)


def setup_c(stage: Path, pid: str) -> str:
    _scaffold_copy(stage, pid)
    ws = PROJ / "workspace"
    # Sparrow's design-stage and curator output — NOT the builder's.
    for rel in ("src/app/globals.css", "src/app/layout.tsx"):
        shutil.copy(ws / rel, stage / rel)
    for rel in ("src/components/ui", "src/lib", "public/assets"):
        shutil.rmtree(stage / rel, ignore_errors=True)
        shutil.copytree(ws / rel, stage / rel)
    (stage / "src/app/page.tsx").write_text(
        "export default function Home() {\n  return <main />;\n}\n")
    run = api._run_for(SRC)
    bb = _bb()
    refs = stage / "refs"
    refs.mkdir()
    for sid, w in steps.load_winners(run).items():
        if w.get("shot") and Path(w["shot"]).is_file():
            shutil.copy(w["shot"], refs / f"{sid}.png")
    (stage / "BUILD_PLAN.md").write_text(build_plan(bb, run, pid))
    base = f"/projects/{pid}/preview"
    text = dossier.render(bb, steps.load_content(run), base)
    return ("Read `BUILD_PLAN.md` before anything else: it is the specification for "
            "this site, section by section.\n\n" + text)


# C+: the same brain, but its composition is handed over as measurements and a
# starting point rather than rules — the agent owns the craft. The guardrails that
# make it this company's site stay: own palette and fonts, real assets, no copying
# a reference's brand, no invented facts.
_RULE_PHRASES = [
    (r"The shape of this section was decided for the whole page at once, by the agent "
     r"that could see all of it\. It is not a suggestion and not yours to revise — the "
     r"page's rhythm is the difference between these shapes\.",
     "What the composer proposed for this section, from the measured sources:"),
    (r"That is the skeleton, not a suggestion\. If it puts the media left, the media goes left\.", ""),
    (r"That is read off the source band's own markup: how many columns, what one item is "
     r"made of, what separates items\. Where it says no border, there is no border; where "
     r"it says a rule, draw a rule\.", "That is read off the source band's own markup."),
    (r"Apply these and no others\.", "Use these where they serve the section."),
]


def _band_counts() -> str:
    counts: dict[str, int] = {}
    for f in (PROJ / "sources").glob("*-b*.png"):
        site = f.name.rsplit("-b", 1)[0]
        counts[site] = counts.get(site, 0) + 1
    return ", ".join(f"{site.replace('_', '.')}: {n} bands" for site, n in sorted(counts.items()))


CPLUS_PREFACE = """# How to use this plan

This plan was written for a section-by-section builder that could not see the page. \
You can, so treat it as MATERIAL, not orders:

- **You own the craft.** Decide the page's sections, their order and how many there \
are, each one's layout, the rhythm between them, the type scale and how boldly the \
palette is used. Judge it from the reference pages in `refs/` — every band of every \
source is there ({bands}) — so the page has the range and pacing of a real page in \
this category, not the minimum. The per-section compositions below are what the \
sources measured; use them as targets, depart where the page is better for it.
- **Copy:** the drafted lines are a starting point. Rewrite for punch — but add no \
facts. No new names (maps, modes, operators, weapons, places), numbers, platforms, \
dates, prices or partners. A section that needs a fact nobody gave gets a visible \
placeholder or is cut.
- **Imagery:** use the curated assets in `public/assets/` (every one of them, if the \
page can carry them) and the hero video. If a section needs an image that does not \
exist, generate it with the asset tool.
- **Identity:** the palette and fonts in `globals.css` / `layout.tsx` are this \
product's. Learn structure, pacing and craft from the references; never reproduce a \
reference's brand — its signature colours, logo treatment or distinctive type.

"""

PROMPT_CPLUS = """Build the website from the material in BUILD_PLAN.md. Read its "How to \
use this plan" first: you own the design — sections, layout, rhythm, type, copy within \
the facts — and the references in refs/ are what it has to stand beside. Use the curated \
assets and the hero video, keep this product's palette and fonts, and never copy a \
reference's brand."""


PROMPT_B = """Build a complete marketing website for {name}.

What it is: {offering}
Who it is for: {audience}
Tone: {tone}
Main action: {primary}. Secondary action: {secondary}.

Reference sites — screenshots of each are in refs/, top to bottom: {sites}. Look at them \
before you design anything; the site should look like it belongs beside them. The owner's \
own files are in public/assets/uploads/ — use them."""

PROMPT_C = """Build the website specified in BUILD_PLAN.md: every section, in order, \
composed on the home page. Follow each section's composition, copy and assets exactly, and \
look at each section's reference band before building it."""


def setup_cplus(stage: Path, pid: str) -> str:
    agents = setup_c(stage, pid)
    plan = (stage / "BUILD_PLAN.md").read_text()
    for pat, repl in _RULE_PHRASES:
        plan = re.sub(pat, repl, plan)
    plan = plan.replace("Build every section below, in this order, each as its own component "
                        "at the file named, then compose them in `src/app/page.tsx` in the "
                        "same order.", "These are the sections Sparrow planned.")
    (stage / "BUILD_PLAN.md").write_text(CPLUS_PREFACE.format(bands=_band_counts()) + plan)
    refs = stage / "refs"
    for f in sorted((PROJ / "sources").glob("*.png")):
        if re.search(r"-(b\d+|sheet)\.png$", f.name):
            shutil.copy(f, refs / f.name)
    return agents


def setup_bplus(stage: Path, pid: str) -> str:
    """B's freedom — the agent designs from the references — with Sparrow as the
    materials and the guardrails instead of the designer: curated assets, a facts
    sheet with what must never be stated, and the rule against copying a brand."""
    rules = setup_b(stage, pid)
    bb = _bb()
    src_assets = PROJ / "workspace" / "public" / "assets"
    dst = stage / "public" / "assets"
    for f in src_assets.iterdir():
        if f.is_file():
            shutil.copy(f, dst / f.name)
    base = f"/projects/{pid}/preview"
    rows = ["# Assets", "",
            "Curated for this product. Use them — every one the page can carry — before "
            "generating anything new. Each image also exists as `--hero` (wide), `--card` "
            "and `--mobile` crops.", ""]
    for a in bb.assets:
        if not (src_assets / Path(a.path).name).is_file():
            continue
        rows.append(f"- `{base}/{a.path}` — {a.kind.value}, {a.provenance.value}, planned for "
                    f"{a.section_id}: {a.brief[:220]}")
    (stage / "ASSETS.md").write_text("\n".join(rows) + "\n")
    b = bb.brief
    facts = ["# Facts", "",
             f"- Product: {b.product_name}", f"- What it is: {b.offering}",
             f"- Audience: {b.audience}", f"- Tone: {b.tone}",
             f"- Actions: {b.primary_action} · {b.secondary_action}", "",
             "## Hard rules (the owner's words — never break them)", ""]
    facts += [f'- "{c.text}"' for c in bb.active_constraints()]
    facts += ["", "## Never state", "",
              "Nothing here is confirmed beyond the lines above. Do not name platforms, "
              "stores, maps, modes, operators, weapons, gadgets or places; do not state "
              "numbers, dates, prices, player counts, durations or ratings. Write around "
              "them, or use a visible placeholder the owner can fill.", ""]
    (stage / "FACTS.md").write_text("\n".join(facts))
    return ("Read `FACTS.md` and `ASSETS.md` before designing.\n\n" + rules)


PROMPT_BPLUS_EXTRA = """

Use the curated images and the hero video listed in ASSETS.md — they were made for this \
product. Everything you may state is in FACTS.md; invent nothing beyond it. Learn layout, \
pacing and craft from the references, but give the product its own look: never reproduce \
a reference's brand — its signature colours, logo treatment or distinctive type."""


def cmd_setup(kind: str) -> None:
    cfg = WorkshopConfig.load()
    pid = PIDS[kind]
    stage = HERE / f"stage-{kind}"
    agents = (setup_b(stage, pid) if kind == "b" else
              setup_bplus(stage, pid) if kind == "bplus" else
              setup_cplus(stage, pid) if kind == "cplus" else setup_c(stage, pid))
    proj = store.project(cfg.root, pid)
    shutil.rmtree(proj.dir, ignore_errors=True)
    store.import_workspace(proj, store.pack(stage))
    store.write_dossier(proj, agents)
    shutil.rmtree(stage)
    print(f"{pid}: {len(list(proj.workspace.rglob('*')))} files, AGENTS.md {len(agents)} bytes")


# ── run ─────────────────────────────────────────────────────────────────────

def _gateway_calls() -> int:
    log = ROOT / "logs" / "gateway.out"
    return log.read_text().count("POST /llm/v1/chat/completions") if log.is_file() else 0


def _sites_line() -> str:
    urls = json.loads((PROJ / "urls.json").read_text())
    primary = (PROJ / "sources" / "primary.txt").read_text().strip() \
        if (PROJ / "sources" / "primary.txt").is_file() else ""
    return ", ".join(u + (" (the main reference)" if primary and primary in u else "")
                     for u in urls)


def cmd_run(kind: str) -> None:
    from sparrow.workshop import studio
    cfg = WorkshopConfig.load()
    pid = PIDS[kind]
    proj = store.project(cfg.root, pid)
    bb = _bb()
    prompt = PROMPT_CPLUS if kind == "cplus" else PROMPT_C if kind.startswith("c") else PROMPT_B.format(
        name=bb.brief.product_name, offering=bb.brief.offering, audience=bb.brief.audience,
        tone=bb.brief.tone, primary=bb.brief.primary_action, secondary=bb.brief.secondary_action,
        sites=_sites_line())
    if kind == "bplus":
        prompt = PROMPT_B.format(
            name=bb.brief.product_name, offering=bb.brief.offering, audience=bb.brief.audience,
            tone=bb.brief.tone, primary=bb.brief.primary_action,
            secondary=bb.brief.secondary_action, sites=_sites_line()) + PROMPT_BPLUS_EXTRA
    if kind == "b" and bb.active_constraints():
        prompt += "\n\nHard rules: " + "; ".join(c.text for c in bb.active_constraints()) + "."
    s = studio.Studio(cfg)
    token = gateway.TOKENS.issue(pid, caps="i")
    calls0, t0 = _gateway_calls(), time.time()
    log = (OUT / f"events-{kind}.jsonl").open("w")
    done = None
    for e in s.turn(proj, prompt, token):
        log.write(json.dumps(e) + "\n")
        log.flush()
        if e["kind"] in ("done", "error"):
            done = e
    s._close(pid)
    summary = {"variant": kind, "seconds": round(time.time() - t0), "llm_requests":
               _gateway_calls() - calls0, "result": done}
    (OUT / f"run-{kind}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "result"}),
          (done or {}).get("kind"), (done or {}).get("reverted"))


# ── measure ─────────────────────────────────────────────────────────────────

USER_FILES = tuple(sorted({p.name.split(".")[0].split("--")[0]
                          for p in (PROJ / "uploads").iterdir()})) \
    if (PROJ / "uploads").is_dir() else ()
COLOR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(")


def _workspace(kind: str) -> Path:
    if kind == "a":
        return PROJ / "workspace"  # only meaningful when the pipeline built it
    return WorkshopConfig.load().root / PIDS[kind] / "workspace"


def cmd_measure(kind: str) -> None:
    from sparrow.audit import unconfirmed
    from playwright.sync_api import sync_playwright
    from PIL import Image

    ws = _workspace(kind)
    out = ws / "out"
    run = api._run_for(SRC)
    confirmed = steps.confirmed_words(run, _bb())
    code_files = [p for p in (ws / "src").rglob("*.tsx")
                  if "/components/ui/" not in p.as_posix()]
    claims, colors, loc = {}, 0, 0
    for p in code_files:
        text = p.read_text()
        loc += text.count("\n")
        colors += len(COLOR_LITERAL.findall(text))
        u = unconfirmed(text, confirmed)
        if u:
            claims[p.relative_to(ws).as_posix()] = u
    pages = store.routes(out)
    broken = store.broken_links(out, look.base_path(ws))

    shots_dir = OUT / "shots"
    shots_dir.mkdir(exist_ok=True)
    media = {"img": 0, "video": 0, "user_files": [], "other": []}
    page_info = {}
    base = look.base_path(ws)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        root = out.resolve()

        def serve(route):
            url = route.request.url
            rel = url[len(look.HOST + base):].split("?")[0].lstrip("/")
            t = (root / rel).resolve()
            if t.is_dir():
                t = t / "index.html"
            if not t.is_file() and t.with_suffix(".html").is_file():
                t = t.with_suffix(".html")
            return route.fulfill(path=str(t)) if t.is_file() and t.is_relative_to(root) \
                else route.fulfill(status=404, body="")

        pg.route("**/*", serve)
        for r in pages:
            pg.goto(look.HOST + base + r, wait_until="load")
            h = pg.evaluate("document.documentElement.scrollHeight")
            for y in range(0, h, 700):
                pg.evaluate(f"window.scrollTo(0,{y})")
                pg.wait_for_timeout(60)
            pg.evaluate("window.scrollTo(0,0)")
            pg.wait_for_timeout(500)
            info = pg.evaluate("""() => {
              const main = document.querySelector('main') || document.body;
              const srcs = [...document.querySelectorAll('img,video,source')].map(e => e.currentSrc || e.src || e.getAttribute('src') || '').filter(Boolean);
              return {height: document.documentElement.scrollHeight,
                      blocks: main.children.length,
                      imgs: document.querySelectorAll('img').length,
                      videos: document.querySelectorAll('video').length, srcs};
            }""")
            page_info[r] = {k: v for k, v in info.items() if k != "srcs"}
            media["img"] += info["imgs"]
            media["video"] += info["videos"]
            for src in info["srcs"]:
                name = src.split("/")[-1]
                (media["user_files"] if any(name.startswith(u) for u in USER_FILES)
                 else media["other"]).append(name)
            png = pg.screenshot(full_page=True)
            im = Image.open(io.BytesIO(png)).convert("RGB")
            im = im.resize((720, round(im.height * 720 / im.width)))
            tag = r.strip("/").replace("/", "_") or "home"
            for i in range(0, im.height, 2400):
                im.crop((0, i, 720, min(im.height, i + 2400))).save(
                    shots_dir / f"{kind}-{tag}-{i // 2400}.jpg", quality=78)
        b.close()

    media["user_files"] = sorted(set(media["user_files"]))
    media["other"] = sorted(set(media["other"]))
    result = {
        "variant": kind, "pages": pages, "page_info": page_info,
        "lines_of_tsx": loc, "color_literals_in_code": colors,
        "unconfirmed_claims": sum(len(v) for v in claims.values()),
        "claims_by_file": claims, "broken_links": len(broken),
        "broken_examples": broken[:8], "media": media,
    }
    (OUT / f"measure-{kind}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("variant", "pages", "lines_of_tsx",
                                             "color_literals_in_code", "unconfirmed_claims",
                                             "broken_links")}),
          "| home:", page_info.get("/"), "| user files used:", media["user_files"])


if __name__ == "__main__":
    cmd, kind = sys.argv[1], sys.argv[2]
    {"setup": cmd_setup, "run": cmd_run, "measure": cmd_measure}[cmd](kind)

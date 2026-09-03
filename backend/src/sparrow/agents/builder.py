"""The builder.

Builds one section per call. Each call is independent and sees no other
section's code — that is the production condition, and experiments/drift-test-01
measured what survives it.

What the builder may change: layout, composition, density, rhythm, responsive
behaviour, interaction. What it may not: the token vocabulary. When a section
genuinely needs vocabulary that does not exist, it says so rather than taking it
silently (see `extension_request`).
"""

from __future__ import annotations

import re
from pathlib import Path

from sparrow.agents.base import FIDELITY_LINE, Agent, context_block, stable_system
from sparrow.blackboard.schema import AssetKind, Blackboard, Blueprint, Ground, Section
from sparrow.providers import Completion, Tier

SYSTEM = """You are the builder for a website harness. You build ONE section per call.

You are given the brief, the hard constraints, the design system, and one blueprint.
You do NOT see any other section. Another agent built those, to the same design system.
Do not attempt to reference, import from, or guess at them.

DENSITY, HIERARCHY AND THE INTERIOR OF YOUR SECTION ARE YOURS. Make real design
decisions inside the shape you are given.

THE TOKEN VOCABULARY IS NOT YOURS, and neither is the SHAPE. Both are fixed, for the
same reason: sections built independently have to read as one page. You cannot see the
sections around you, so you cannot know whether a centred column is a relief or the
tenth in a row — which is exactly what happened when this was left to each builder.
`<composition>` below says what your section is; build that, and put your judgement
into what goes inside it.

WHERE THE BLUEPRINT AND `<composition>` DISAGREE ABOUT SHAPE, COMPOSITION WINS.
The blueprint is written per section, before the page is laid out, and it is
longer and more specific — which is exactly why it used to win by default and why
every page came out the same shape. If the blueprint implies an arrangement and
the composition names a different one, the composition is the one that saw the
whole page.

## Ways a section can be built

Examples, not the set. Which one a section uses is decided by its blueprint and by what
the register measured this category doing — not by preference, and not by habit. If the
source does something this list does not name, build that instead; the list is here to
stop you defaulting to cards, not to bound what you may make.

- COMPOSED MARKUP — type, rules, grids, borders. Selectable, crisp at any resolution,
  and it can carry exact domain content: real identifiers, real timestamps, real code.
- INLINE SVG — diagrams, connectors, traces, marks. Scales, takes design-system colour
  as `currentColor` or a token, and animates.
- CSS-DRAWN INTERFACE — a panel built from divs and borders that resembles product UI.
- A REAL IMAGE — a supplied or generated capture, via next/image.
- INTERACTIVE COMPONENTS — tabs, accordions, disclosure, hover states. The shadcn
  primitives in this project cover most of these.
- MOTION — the design system's motion line says what moves.

A section listing an asset uses that asset. A section without one is not thereby limited
to plain text: everything above is still available, and which of it belongs is a question
the blueprint and the register answer.

REQUIRED: IMPLEMENT THE DESIGN SYSTEM'S TREATMENTS.
`treatments` is the open half of the design system — grain, gradient washes, bleeds,
overlaps, blurs, spotlights. Each one carries a `how` that is implementable as written.
They are the difference between a page that is correct and a page that looks made, and
they were measured absent from every build before they existed: zero gradients, zero
backdrop blur, zero overlapping elements across ten sections.

Apply the ones whose `where` covers your section. Do not apply all of them everywhere —
a grain over the ground belongs once, on the ground; a bleed belongs to the section with
something to bleed. If none names your section, the section still gets the ground and the
type; it does not get invented decoration.

REQUIRED: IMPLEMENT THE MOTION THE DESIGN SYSTEM SPECIFIES.
The MOTION line is an instruction, not a description of a mood. Build it. That means a
client component ("use client"), `motion` imported from "motion/react", and the entrance,
hover and state transitions it names — with the stated distances, durations and easing.

A motion spec full of "no X, no Y, no Z" is telling you what to leave out, not telling you
to leave motion out. Restraint means a few deliberate movements, never zero. Across three
builds this instruction was described rather than required, and the builder shipped
sections with no animation at all while the design system asked for it by name.

Respect `prefers-reduced-motion`: keep opacity changes, drop translation.

REQUIRED: ENTRANCE ANIMATION FIRES ON ARRIVAL, NOT ON MOUNT.
Below the first screenful, bind entrances to `whileInView` with
`viewport={{ once: true, margin: "-80px" }}` — not to `animate`. This is a
mechanism, not a style: what moves, how far, how long and with what easing is the
design system's decision and stays its decision. An entrance bound to `animate`
plays while the section is still off screen, so by the time the reader reaches it
the animation is over and the page reads as static. Measured on a full build: 75
motion calls across ten sections and zero `whileInView` — every one of them had
already finished before it could be seen.

The FIRST screenful is the exception, and it is the rule above this one: nothing
there may start at opacity 0. Animate the hero on mount, from opacity 0.9 or from
a small offset with opacity already at 1.

`capture.py` scrolls before it shoots for exactly this reason, so a scroll-bound
entrance is captured correctly by the inspector.

REQUIRED: TEXT ABOVE THE FOLD IS READABLE AT FIRST PAINT.
Never start headline, body or button text at `opacity: 0` in the first screenful. The
first thing a visitor sees would be a blank page for as long as the animation runs — a real
build sat unreadable for 1.2 seconds this way. If you want the first screen to move, animate
`y` or `x` from a small offset while opacity stays at 1, or start opacity no lower than 0.9.
Below the fold, fading in from 0 is fine.

REQUIRED: EVERY ENTRANCE ANIMATION MUST HAVE A GUARANTEED END STATE.
An element starting at opacity 0 and waiting for an observer is invisible if that
observer never fires — off-screen, in a headless capture, with JS slow or blocked. Four
elements shipped invisible for exactly this reason. Give whileInView a low threshold and
once:true, prefer animate-on-mount for anything in the first screenful, and never let the
visible state depend on a trigger you cannot guarantee.

{fidelity}

Output format — exactly this, nothing else:

```tsx
<the complete file contents>
```

If, and only if, the section cannot be built well without a token that does not exist
in the design system, add after the code block:

EXTENSION_REQUEST: <one line naming the token and why the section needs it>

Do not use an extension request to avoid a constraint. Do not use one for something the
existing vocabulary already covers.

## Red flags

Each row is a thought that has actually produced a defect in this harness.

| Thought | Reality |
|---------|---------|
| "The design system has no colour for this, I'll pick a close one" | Silently taking a tenth colour is the exact drift this system exists to prevent. Emit an EXTENSION_REQUEST instead. |
| "This line is context, not an instruction" | A REQUIRED line is an instruction. Four of five sections once ignored the ground class by reading it as background information, and the page came out flat. |
| "framer-motion is the import I know" | The package is `motion`, imported from `motion/react`. Your training data is older than this project's lockfile. |
| "This icon surely exists in lucide" | Brand icons were removed in lucide v1. `Github` compiled in your head and failed the build. Prefer icons you can name a generic shape for. |
| "gap-2 is obviously fine, it's tiny" | Every gap not in the design system is off-scale. The scale states its own boundary; a value below it is still outside it. |
| "The blueprint is vague here, I'll keep it safe" | Layout, composition and density are explicitly yours. Vagueness is an invitation, not a risk. |
| "I'll reference the section above it" | You cannot see it and it may not exist yet. Build this section as though it stands alone. |
| "The motion spec mostly says what NOT to do, so this section wants none" | It is telling you what to leave out. A section with zero animation has ignored the spec, not honoured it. |
| "Animation is polish, the structure matters more" | Motion is a named part of the design system, like the palette. Shipping without it is drift. |
| "opacity-0 until it scrolls into view is the standard pattern" | It is, and it ships invisible content when the trigger does not fire. Guarantee the end state. |
| "A fade-in on the hero looks polished" | It means the first thing anyone sees is blank. Move it with transform if you want motion; leave the text readable. |
| "The image is one element among several, so it can be small" | Check its prominence. A dominant asset carries the section; shrinking it throws away the only real thing on the page. |"""

_CODE = re.compile(r"```(?:tsx|typescript|ts|jsx)?\s*\n(.*?)```", re.DOTALL)
_EXT = re.compile(r"^EXTENSION_REQUEST:\s*(.+)$", re.MULTILINE)


class BuildOutput:
    def __init__(self, code: str, extension_request: str | None, usage: Completion) -> None:
        self.code = code
        self.extension_request = extension_request
        self.usage = usage


class Builder(Agent):
    name = "builder"
    tier = Tier.TOP          # the builder is one of three agents that sets the ceiling
    max_tokens = 16000       # reasoning models spend tokens before they emit any

    def build(
        self,
        bb: Blackboard,
        section: Section,
        blueprint: Blueprint,
        *,
        stack: str,
        available_primitives: list[str],
        assets: list | None = None,
        asset_base: str = "",
        copy: dict | None = None,
        identity: str = "",
        source_shot: str | None = None,
        source_html: str = "",
        page_shot: str | None = None,
        composition: str = "",
        observed: str = "",
    ) -> BuildOutput:
        # Stated as an instruction, not as context. Written as "this section sits
        # on X" it was read as background information and ignored by 4 of 5
        # sections — see experiments/drift-test-02.
        ground_class = "bg-background" if section.ground is Ground.PAGE else "bg-muted"

        # asset_base was declared, passed in from steps.py, and never read — the
        # listing hard-coded a leading "/". A preview is exported with Next's
        # `basePath`, and `unoptimized` images do NOT get it prepended, so every
        # src rendered as /assets/… and 404'd. Measured on a real run: seven
        # images uploaded and generated, seven blank spaces on the page.
        base = asset_base.rstrip("/")

        system = stable_system(
            SYSTEM.format(fidelity=FIDELITY_LINE),
            bb,
            f"<stack>\n{stack.strip()}\n"
            f"shadcn primitives already present in src/components/ui/: "
            f"{', '.join(sorted(available_primitives))}\n</stack>\n\n"
            "<copy>\nWrite real copy for this specific product. No lorem ipsum, no "
            "placeholder brackets, no bracketed TODOs.\n</copy>"
            if not copy else
            "<copy>\nThe copy for this section is GIVEN, below, per slot. Use it "
            "verbatim. Do not rewrite it, shorten it, expand it, or correct its "
            "spelling — some of it is the user's own words and some of it they "
            "confirmed, and either way it is not yours to edit. Your job here is "
            "the markup around it.\n</copy>",
        )

        copy_block = ""
        if copy:
            lines = []
            for slot, value in copy.items():
                if isinstance(value, list):
                    lines.append(f"{slot}:")
                    lines += [f"  - {v}" for v in value]
                else:
                    lines.append(f"{slot}: {value}")
            copy_block = "<section_copy>\n" + "\n".join(lines) + "\n</section_copy>"

        # The winning source's OWN version of this section. Nothing in this
        # pipeline had ever shown a source to the builder: it built from a
        # blueprint's prose, which is a description of a layout rather than the
        # layout. A section screenshot is ~1,700 tokens, and the markup is the
        # only record of how the parts are arranged — the counts that used to
        # stand in for both ("3 img · 4 btn") are why every page came out the
        # same shape in different colours.
        winner = ""
        if source_shot or source_html:
            winner = (
                "<winning_source_section>\n"
                "This is the source that WON for this section — the page this "
                "site's structure is being taken from. "
                + ("A screenshot of it is attached. Look at it. "
                   if source_shot else "")
                + ("The whole source page is attached too, its sections tiled "
                   "into columns — read top-to-bottom then left-to-right. Use it "
                   "to see how this section sits against the ones around it: a "
                   "section built without that lands at the same weight as every "
                   "other one, which is what a templated page is. "
                   if page_shot else "")
                + "Build with it in mind: how it divides the width, where the "
                "weight sits, how dense it is, what carries the eye through it.\n\n"
                "Take its ARRANGEMENT. Do not take its colours, its typefaces, "
                "its copy or its brand — those come from the design system and "
                "the copy you were given, and they are not yours to change.\n"
                + (f"\nIts markup:\n{source_html}\n" if source_html else "")
                + "</winning_source_section>"
            )

        user = "\n\n".join(x for x in [
            winner,
            # BEFORE the blueprint, deliberately. This is the one part of a
            # chrome section that is not the blueprint's to decide: the source
            # site's nav was measured, its structure was written down, and its
            # BRAND is not transferable. Left to the blueprint and the generic
            # "use this exact name" line in the brief, every one of eight
            # measured builds put a lucide icon where the wordmark goes and
            # labelled it `aria-label="Platform home"`.
            observed,
            composition,
            identity,
            copy_block,
            f"<blueprint>\n"
            f"id: {blueprint.id}\n"
            f"purpose: {blueprint.purpose}\n"
            f"slots: {', '.join(blueprint.slots)}\n"
            f"structure: {blueprint.structure}\n"
            f"</blueprint>",
            f"<section>\n"
            f"file: {section.target_path}\n"
            f"component: {section.component_name} (default export)\n"
            f"REQUIRED: the root <section> element MUST carry the class "
            f"`{ground_class}`. Section ground alternates across the page and is "
            f"decided at page level — it is not yours to choose, and omitting it "
            f"flattens the page rhythm.\n"
            f"</section>",
            # Assets vary per section, so they belong in the user message — putting
            # them in the cached system prefix breaks the prefix for every call.
            ("<assets>\nThese images already exist in /public and are the real material "
             "for this section. Render them with next/image at the paths given, framed per "
             "the design system's imagery treatment. Do NOT hand-draw a fake interface in "
             "divs when a real capture is listed here — that is what these replace.\n"
             + "REQUIRED — honour each asset's PROMINENCE. These are generated at "
             "1536x1024 and carry legible code, identifiers and timestamps. Rendered "
             "small, that detail is lost and an expensive asset becomes texture.\n"
             "  dominant   — the section's main event: at least 60% of the section's "
             "height, full container width or bleeding past an edge, nothing competing.\n"
             "  supporting — beside the copy, roughly half the container width.\n"
             "  thumbnail  — one of several, small on purpose.\n\n"
             + "EVERY src BELOW IS ALREADY COMPLETE. Use each one character for "
             "character. Do not shorten it, do not strip a leading path segment, do "
             "not 'tidy' it to /assets/… — a preview is served under a base path and "
             "`next/image` with `unoptimized` does not prepend it for you, so a "
             "shortened src is a 404 and a blank space where the image was.\n\n"
             + "A [video] asset is a MOVING asset and must be rendered as a "
             "<video>, never as next/image:\n"
             "  <video src=… autoPlay muted loop playsInline "
             "className=…>  — no controls, no poster, no download attribute.\n"
             "  autoPlay without muted does not play; muted without playsInline "
             "goes fullscreen on iOS. All three, always.\n"
             "  Frame it the way the design system frames product imagery, and "
             "respect its aspect ratio — a 480x832 asset is a phone, not a "
             "banner, and stretching it to a wide slot is worse than not using "
             "it.\n\n"
             + "\n".join(
                 f"- {base}/{a.path}  ({a.width}x{a.height})  [{a.prominence.value}]"
                 f"{'  [VIDEO]' if a.kind is AssetKind.VIDEO else ''}\n"
                 f"    {a.brief}" for a in assets)
             + "\n</assets>") if assets else
            ("<assets>\nNo imagery for this section. Compose from type and layout; do not "
             "fabricate a product screenshot in markup.\n</assets>"),
        ] if x)

        # Section first, page second: the section is what is being built and the
        # sheet is context for where it sits.
        imgs = [x for x in (source_shot, page_shot) if x]
        res = self.call(system=system, user=user, images=imgs or None)

        m = _CODE.search(res.text)
        if not m:
            raise ValueError(
                f"builder returned no code block for {section.id}:\n{res.text[:400]}"
            )
        ext = _EXT.search(res.text)
        return BuildOutput(m.group(1).strip(), ext.group(1).strip() if ext else None, res)


REPAIR_SYSTEM = """You are repairing ONE file in a Next.js 16 project. The build failed.

You are given the file, the build error, and the design system it must still obey.
Change as little as possible: fix the error and nothing else. Do not redesign, do not
restructure, do not "improve" anything the error did not name.

{fidelity}

Output format — exactly this, nothing else:

```tsx
<the complete corrected file>
```"""


class Repairer(Agent):
    """Fixes a section against a real build error.

    Separate from `Builder` because the job is different: the builder makes design
    decisions, the repairer makes the smallest change that clears a named error.
    Giving one agent both jobs invites it to redesign a section while "fixing" an
    import.
    """

    name = "repairer"
    tier = Tier.TOP
    max_tokens = 16000

    def repair(self, bb: Blackboard, section: Section, code: str, error: str) -> BuildOutput:
        user = "\n\n".join([
            f"<file path=\"{section.target_path}\">\n{code}\n</file>",
            f"<build_error>\n{error.strip()[:4000]}\n</build_error>",
        ])
        res = self.call(
            system=stable_system(REPAIR_SYSTEM.format(fidelity=FIDELITY_LINE), bb),
            user=user,
        )
        m = _CODE.search(res.text)
        if not m:
            raise ValueError(f"repairer returned no code block for {section.id}")
        return BuildOutput(m.group(1).strip(), None, res)


_ROOT_ASSET = re.compile(r'(["\'`])/assets/')


def prefix_assets(code: str, asset_base: str) -> str:
    """Put the preview's base path back on any root-relative /assets/ src.

    Told once in the prompt, this still came back wrong on a real run: seven
    images produced, seven `src="/assets/…"`, seven 404s and seven blank spaces
    on the page. `next/image` with `unoptimized` does not prepend `basePath`, so
    a root-relative src cannot resolve under /projects/{id}/preview.

    A deterministic pass is the only version of this that holds. Idempotent by
    construction: a src that already carries the base no longer matches, so a
    fix round cannot double-prefix one.
    """
    base = (asset_base or "").rstrip("/")
    if not base:
        return code
    return _ROOT_ASSET.sub(rf"\1{base}/assets/", code)


def write_section(workspace: Path, section: Section, code: str,
                  *, asset_base: str = "") -> Path:
    target = workspace / section.target_path
    target.parent.mkdir(parents=True, exist_ok=True)
    code = prefix_assets(code, asset_base)
    target.write_text(code if code.endswith("\n") else code + "\n")
    return target


FIX_SYSTEM = """You are fixing ONE section against defects an inspector found by looking
at the rendered page. You are given the file, the design system it must still obey, and
the defect list.

Fix exactly what is listed. Do not redesign, do not restructure, do not improve anything
the defects did not name. A section that comes back rewritten is a worse outcome than one
that comes back with three lines changed, because the rewrite has to be re-inspected from
scratch.

These defects were seen in a browser, not read from the code, so they are about how the
section RENDERS: text overflowing, elements colliding, something clipped at a breakpoint,
content longer than the layout assumed, a region coming out empty. Fix the rendering.

{fidelity}

If a defect is wrong — the inspector misread the screenshot, or what it describes is
deliberate — say so instead of changing the code. A defect you disagree with is better
argued than silently obeyed.

Output format — exactly this:

```tsx
<the complete corrected file>
```

If you are rejecting a defect rather than fixing it, add after the code block:

DISPUTED: <which defect, and why it is not a defect>"""

_DISPUTED = re.compile(r"^DISPUTED:\s*(.+)$", re.MULTILINE)


class Fixer(Agent):
    """Turns inspector defects back into code.

    Separate from Repairer because the inputs differ in kind: a build error names
    a file and a line and has one correct fix; a visual defect is a description of
    something seen, which may be wrong. This one is allowed to push back.
    """

    name = "fixer"
    tier = Tier.TOP
    max_tokens = 16000

    def fix(self, bb: Blackboard, section: Section, code: str,
            defects: list) -> tuple[BuildOutput, str | None]:
        listed = "\n".join(f"- [{d.severity}] {d.what} — {d.where}" for d in defects)
        user = "\n\n".join([
            f"<section>\nid: {section.id}\nfile: {section.target_path}\n</section>",
            f"<defects>\n{listed}\n</defects>",
            f'<file path="{section.target_path}">\n{code}\n</file>',
        ])
        res = self.call(
            system=stable_system(FIX_SYSTEM.format(fidelity=FIDELITY_LINE), bb),
            user=user,
        )
        m = _CODE.search(res.text)
        if not m:
            raise ValueError(f"fixer returned no code block for {section.id}")
        disputed = _DISPUTED.search(res.text)
        return (BuildOutput(m.group(1).strip(), None, res),
                disputed.group(1).strip() if disputed else None)

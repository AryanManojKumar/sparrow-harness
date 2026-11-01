"""The site dossier: what the studio agent knows about the site it is editing.

The pipeline made dozens of recorded decisions — palette, type steps, which
section carries which treatment, which words the user confirmed — and none of
that is visible in the code it produced. An agent dropped into the workspace
cold sees ten .tsx files and re-derives a design system from them, badly: in
the spike it reused tokens correctly but shipped a nav link that 404s under
the preview's base path and check marks invisible on a dark card. Both were
facts the blackboard already held.

Same shape as §4's argument for the brief: small and complete, injected whole,
never retrieved. The office writes it from the blackboard; the workshop puts
it at the workspace root as AGENTS.md, read-only inside the jail, where DeepSeek
Harness loads it into every request.

What goes in is FACTS about this site and the invariants of this build — not
taste. The design system is the design agent's own recorded transcript (§6),
handed to the next builder exactly as it was handed to the first.
"""

from __future__ import annotations

from sparrow.blackboard.schema import Blackboard, Provenance


def _lines(items) -> str:
    return "\n".join(f"- {x}" for x in items)


def render(bb: Blackboard, content: dict, preview_base: str) -> str:
    b, ds = bb.brief, bb.design_system
    out: list[str] = []
    name = (b.product_name if b else "") or bb.project_id

    out += [f"# {name} — website dossier",
            "",
            "This is a finished marketing website, generated from a brief and real "
            "material supplied by its owner. You are editing it on the owner's behalf. "
            "The owner is not an engineer: they see the rendered page, not the code.",
            ""]

    if b:
        out += ["## What the site is for", "",
                f"- **Offering:** {b.offering}",
                f"- **Audience:** {b.audience}",
                f"- **Tone:** {b.tone}",
                f"- **Primary action:** {b.primary_action}"]
        if b.secondary_action:
            out.append(f"- **Secondary action:** {b.secondary_action}")
        out.append("")

    active = bb.active_constraints()
    if active:
        out += ["## The owner's hard requirements (verbatim — never break these)", "",
                _lines(f'"{c.text}"' for c in active), ""]

    confirmed, drafted = [], []
    for sid, entry in content.items():
        prov = entry.get("provenance") or {}
        for slot, value in (entry.get("slots") or {}).items():
            text = ", ".join(value) if isinstance(value, list) else str(value)
            if not text.strip():
                continue
            row = f"{sid} · {slot}: {text[:200]}"
            (confirmed if prov.get(slot) == "user_supplied" else drafted).append(row)
    out += ["## What is true",
            "",
            "Only the owner's own words are facts. Names, customers, figures, prices, "
            "certifications, integrations and quotes that are not below or in the "
            "brief must not appear on the page — not even plausible ones. When a "
            "request needs a fact you do not have, build it with a visible "
            "placeholder such as `[Your price]` and say so in your reply.",
            ""]
    if confirmed:
        out += ["Confirmed by the owner:", "", _lines(confirmed), ""]
    if drafted:
        out += ["Drafted by the pipeline (may be reworded, but adds no facts):", "",
                _lines(drafted[:40]), ""]

    if ds:
        out += ["## Design system (recorded by the design agent — hold to it)", "",
                f"**Atmosphere:** {ds.atmosphere}", "",
                f"**Signature:** {ds.signature}", ""]
        out += ["Colours are CSS variables in `src/app/globals.css`, used through "
                "Tailwind as `bg-<token>`, `text-<token>`, `border-<token>`. Use only "
                "these; do not write hex, rgb or oklch values into components.", "",
                "| token | name | role |", "|---|---|---|"]
        out += [f"| `{c.token}` | {c.name} | {c.role} |" for c in ds.colors]
        out += ["", f"Fonts: display `{ds.font_display}`, body `{ds.font_body}`"
                + (f", mono `{ds.font_mono}`" if ds.font_mono else "")
                + f". Weights in use: {', '.join(str(w) for w in ds.font_weights)}.", "",
                "Type steps — copy these classes exactly:", "",
                "| step | classes | use |", "|---|---|---|"]
        out += [f"| {t.name} | `{t.classes}` | {t.use} |" for t in ds.type_steps]
        spacing = [("section padding", ds.section_padding), ("tight", ds.section_padding_tight),
                   ("loose", ds.section_padding_loose), ("container", ds.container),
                   ("wide container", ds.container_wide), ("grid gap", ds.grid_gap),
                   ("inline gap", ds.inline_gap), ("stack tight", ds.stack_tight),
                   ("stack loose", ds.stack_loose), ("card radius", ds.radius_card),
                   ("base radius", ds.radius_base), ("shadow at rest", ds.shadow_rest),
                   ("shadow on hover", ds.shadow_hover)]
        out += ["", "Spacing and surfaces:", "",
                _lines(f"{k}: `{v}`" for k, v in spacing if v)]
        if ds.radius_scale:
            out.append(f"- the whole radius vocabulary: {', '.join(f'`{r}`' for r in ds.radius_scale)}")
        if ds.shadow_scale:
            out.append(f"- the whole shadow vocabulary: {', '.join(f'`{s}`' for s in ds.shadow_scale)}")
        if ds.treatments:
            out += ["", "Surface treatments (each has its place; do not spread them):", "",
                    _lines(f"**{t.name}** — where: {t.where}; how: `{t.how}`" for t in ds.treatments)]
        out += ["", f"Imagery: {ds.imagery_treatment}", f"Motion: {ds.motion}", ""]

    if bb.sections:
        out += ["## The home page, top to bottom", "",
                "| section | file | sits on | shape |", "|---|---|---|---|"]
        for s in sorted(bb.sections, key=lambda s: s.order):
            sig = " · carries the signature" if s.carries_signature else ""
            out.append(f"| `{s.id}` | `{s.target_path}` | {s.ground} | "
                       f"{s.archetype or s.width.value}{sig} |")
        out += ["", "`src/app/page.tsx` composes them. A section's root element does "
                "not necessarily carry an `id`: before linking to one, check that the "
                "target element has the matching `id`, and add it if it is missing.", ""]

    if bb.assets:
        out += ["## Images", "",
                f"Files live in `public/assets/`. Reference them as "
                f"`{preview_base}/assets/<file>` (see Build rules).", ""]
        label = {Provenance.USER_SUPPLIED: "the owner's own", Provenance.RESTYLED:
                 "the owner's, restyled", Provenance.GENERATED: "generated"}
        out += [_lines(f"`{a.path}` — {label.get(a.provenance, a.provenance)}, "
                       f"used in `{a.section_id}`: {a.brief[:120]}" for a in bb.assets), ""]

    out += ["## Build rules (break one and the page breaks)", "",
            f"- The site is a Next.js static export served under the base path "
            f"`{preview_base}`. `next.config.ts` sets it; never change that file.",
            "- Links between pages use `next/link` — `<Link href=\"/pricing\">` — which "
            "adds the base path. A plain `<a href=\"/pricing\">` 404s.",
            "- Links to a home-page section from another page use `/#<section id>` "
            "through `next/link`; a bare `#id` only works on the home page itself.",
            f"- Image `src` values start with `{preview_base}/assets/`. `next/image` "
            "here is unoptimized and does NOT add the base path.",
            "- Static export: no API routes, no server actions, no `next/headers`, no "
            "runtime data fetching. Dynamic routes need `generateStaticParams`.",
            "- New imagery comes from the `generate_asset` tool, which saves into "
            "`public/assets/` and returns the exact `src`. Never reference a file that "
            "does not exist, and never replace the owner's own images with generated ones.",
            "- Dependencies are fixed; adding a package fails the build. Available: "
            "React, `motion`, `lucide-react`, `radix-ui`, and the shadcn components "
            "in `src/components/ui/`.",
            "- A new page reuses the site's `Nav` and `Footer` sections so it looks like "
            "the same site, and is added to the nav where an owner would expect it.",
            "- Entrance animation uses `whileInView`, never mount-time animation; "
            "respect `useReducedMotion`.",
            "- After a change, run `./node_modules/.bin/next build` and fix every error "
            "before you finish.",
            "",
            "## How to answer",
            "",
            "- Change what was asked and nothing else. Read a section's file before "
            "editing it.",
            "- Finish with two or three plain sentences an owner would understand: what "
            "changed and where to look. No file names, no code, no jargon.",
            ""]
    return "\n".join(out)

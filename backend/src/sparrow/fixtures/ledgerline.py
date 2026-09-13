"""The design system from experiments/drift-test-01, as data.

Kept as a fixture because it is the only design system with measured results
attached to it, which makes it the regression baseline for the audit.
"""

from sparrow.blackboard.schema import Brief, Color, Constraint, DesignSystem, TypeStep

BRIEF = Brief(
    # Named, because every stage downstream now has to agree on it and a fixture
    # with `product_name=""` silently exercises the "not given" branch — which
    # is the branch all eight real projects took and the reason this fixture
    # gained the field.
    product_name="Ledgerline",
    category="B2B SaaS landing page",
    offering=(
        "Continuous SOC 2 compliance automation. Connects to a company's cloud "
        "infrastructure, monitors controls continuously, and produces audit-ready evidence."
    ),
    audience=(
        "Technical founders and heads of compliance at Series A-C fintech companies. "
        "Bought by people who have been through one painful audit already."
    ),
    tone=(
        "Precise, calm, credible. Understated rather than loud. The reader is technical "
        "and allergic to marketing language."
    ),
    primary_action="Book a demo",
    secondary_action="Read the docs",
)

CONSTRAINTS = [
    Constraint(id="c0001", text="no blue - our competitor is blue"),
    Constraint(id="c0002", text="must mention SOC 2"),
    Constraint(id="c0003", text="no stock photos of people"),
    Constraint(id="c0004", text="no countdown timers or fake urgency"),
]

DESIGN_SYSTEM = DesignSystem(
    atmosphere=(
        "A ledger, not a dashboard. Warm paper ground, hairline rules, and text that sits "
        "flat on the page — the register of an auditor's working papers rather than a "
        "monitoring product. Nothing glows. Evidence is presented, not sold."
    ),
    signature=(
        "The control ledger: a hairline-ruled table of live controls, each row carrying its "
        "SOC 2 criterion, its state and its timestamp, bleeding off the right edge of the hero."
    ),
    key_characteristics=[
        "Deep evidence green as the only saturated colour, on CTAs and nothing else",
        "Amber appears at most once per section, and only to mark an exception",
        "Hairline borders instead of cards wherever a boundary is needed",
        "No glow, no coloured shadow, no gradient of any kind",
        "Numbers set at the same weight as the labels beside them — no hero statistics",
    ],
    colors=[
        Color(token="background", name="Working Paper", value="oklch(0.993 0.004 95)", role="warm off-white page ground"),
        Color(token="foreground", name="Ledger Ink", value="oklch(0.22 0.012 95)", role="body text"),
        Color(token="primary", name="Evidence Green", value="oklch(0.45 0.10 155)", role="CTAs and emphasis — the only saturated colour"),
        Color(token="primary-foreground", name="Paper White", value="oklch(0.985 0.006 95)", role="text on green"),
        Color(token="accent", name="Exception Amber", value="oklch(0.78 0.145 72)", role="one emphasis per section maximum; marks an exception"),
        Color(token="muted", name="Bond", value="oklch(0.965 0.006 95)", role="alternating section grounds"),
        Color(token="muted-foreground", name="Pencil", value="oklch(0.52 0.014 95)", role="secondary text"),
        Color(token="border", name="Rule", value="oklch(0.90 0.008 95)", role="hairlines"),
        Color(token="card", name="Leaf", value="oklch(1 0.002 95)", role="raised surfaces"),
    ],
    forbidden_hues=[(200, 290)],
    font_display="Geist",
    font_body="Geist",
    font_weights=[400, 500, 600],
    type_steps=[
        TypeStep(name="display", classes="text-5xl md:text-6xl leading-[1.05] tracking-tight",
                 use="hero headline ONLY — no other section may use this step"),
        TypeStep(name="h2", classes="text-3xl md:text-4xl leading-tight", use="section headings"),
        TypeStep(name="h3", classes="text-xl leading-snug", use="card titles"),
        TypeStep(name="body", classes="text-base leading-relaxed", use="prose"),
        TypeStep(name="small", classes="text-sm leading-normal", use="captions, labels"),
        TypeStep(name="eyebrow", classes="text-xs tracking-widest uppercase font-medium",
                 use="section labels"),
    ],
    section_padding="py-24 md:py-32",
    container="max-w-6xl px-6",
    grid_gap="gap-8",
    inline_gap="gap-3",
    stack_tight="space-y-4",
    stack_loose="space-y-8",
    radius_base="0.5rem",
    radius_card="rounded-lg",
    radius_input="rounded-md",
    radius_full_allowed="avatars only",
    shadow_rest="shadow-sm",
    shadow_hover="shadow-md",
    imagery_treatment=(
        "Product screenshots sit in a plain rounded container with a hairline border and "
        "shadow-md, bleeding off the right edge of the container on desktop. No browser "
        "chrome, no perspective tilt, no gradient backdrop."
    ),
    motion=(
        "Entrance only: fade up 12px, 400ms, ease-out, staggered 60ms across siblings. "
        "Hover: 150ms colour transition on interactive elements. Nothing else moves."
    ),
)

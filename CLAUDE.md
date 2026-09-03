# Website Builder Harness — Project Context

> This document is **context, not a task list**. It exists so a new session understands the
> architecture and the decisions behind it without re-explaining. Nothing here is an
> instruction to start building.

**Status:** built and running. Backend, frontend, and a full pipeline that takes a
sentence to an exported site. Several projects built end to end.
**Last updated:** 2026-09-02

---

## 1. What this is

An agent harness — a system, not a model — that builds business websites end to end from a
prompt. Scoped to business sites: B2B SaaS, portfolios, local services, small commerce.

Comparable products (Lovable, Emergent) take a one-line prompt and guess at everything else.
This one refuses to guess at the two things that actually determine whether the output is
usable: **what the site is for**, and **what real material it has to work with**.

## 2. Product thesis

**The objective: as close to the source as its structure allows, and as creative as the
source is.** Not "a correct page for this brief" — a page that could sit beside the
reference sites without looking like the templated one. Both halves are load-bearing.
*Close* without *creative* is a tidy page nobody remembers; *creative* without *close* is
a demo reel that does not read as a product. Everything below serves that sentence.

Two ways it fails, both measured on real builds and both worth naming because they look
nothing alike and have the same cause — a decision nobody was allowed to make:

- **Flat.** Every section the same width, the same rhythm, no surface treatment. Ten good
  sections that read as a template. Cause: the schema had no field for the decision, so
  no agent made it.
- **Busy.** Technique everywhere, a signature motif repeated until it is wallpaper.
  Cause: the vocabulary was open but nothing allocated it, so every section took some.

The fix for both is the same shape: **vocabulary open, budget closed.** An agent may
invent any technique; the pass that can see the whole page decides where it lands and how
often. See §6.

Two differentiators. Everything else is infrastructure in service of these.

**Goal elicitation before generation.** The run starts by pinning down intent. Open-ended input
("I want a website") gets autocomplete chips — B2B SaaS platform, portfolio, local service — that
expand into a structured brief. A detailed goal upfront skips ahead. Nothing is generated until
the brief exists.

**Real content, not filler.** Every AI-built business site dies on lorem ipsum and stock photos.
This system asks the user for their actual material — copy, and especially product/dashboard
imagery — and shows source snippets as reference so the user knows what is being asked for and
why. This is the single most valuable idea in the design and the least solved elsewhere.

## 3. Architecture: blackboard, not agent mesh

**No agent talks to another agent.** Free-form A2A produces unbounded loops, context explosion,
and no way to debug why an output changed.

Instead: one shared, versioned artifact — the blackboard. Agents read it and propose **diffs**.
An orchestrator applies or rejects them. Every state transition is recorded, so any run is
replayable and any regression is traceable to the diff that caused it.

```
                    ┌──────────────┐
   read ──────────► │  BLACKBOARD  │ ◄────────── apply / reject
                    │  (versioned) │
                    └──────────────┘
                            ▲
                            │ diffs
        ┌───────────┬───────┴──────┬────────────┐
     design      content        builder      observer
```

### Blackboard shape

| Field | Holds |
|---|---|
| `brief` | structured goal — audience, category, tone, offering, hard requirements |
| `constraints` | short verbatim strings, injected into every agent prompt (see §4) |
| `sources` | primary reference + secondary checklist, with extraction artifacts |
| `design_system` | the design agent's recorded decisions — palette, type scale, spacing, radii, shadows, imagery treatment |
| `sitemap` | pages and section order |
| `sections[]` | per-section state: blueprint, content, assets, build status |
| `assets` | uploaded originals + derived variants (see §7) |
| `content` | copy, per section, with provenance (user-supplied vs. drafted) |
| `decisions` | append-only log with supersede traces |

Stored as Postgres JSONB. Backend is FastAPI + Postgres + Docker with a job queue; Redis for
queue and state.

## 4. Goal memory: a document, not an index

The concern is real — the goal must not fade out of the context window over a long run. But
**vector embeddings are the wrong tool for this specific problem**, for two reasons:

**Retrieval fails by omission.** A brief for one site is a few thousand tokens — small enough to
inject in full, always, into every agent. Introducing retrieval buys nothing and adds a silent
failure: the design agent queries "color direction," and the line where the user said *"don't use
blue, our competitor is blue"* doesn't come back, because it embeds as competitor-talk. The
constraint doesn't error. It just isn't there.

**Append-only stores can't handle contradiction.** The user says "friendly and approachable" in
the brief, then forty minutes later, looking at a draft: "actually more serious, we sell to
banks." That is a *replacement*, not an addition. A vector store holds both, both retrieve, both
look equally relevant, and the agent averages them into mush.

So the model is:

- **The brief is a structured document, injected whole.** A small **librarian** step runs whenever
  the user says something new: it reads the statement plus the current brief and emits a diff —
  add, revise, or **supersede**. Superseded items keep a one-line trace of what they were and when
  they changed. That trace is what makes tone drift debuggable and the run replayable.
- **Hard constraints are a separate verbatim list.** Short strings — "no blue", "must mention
  SOC 2", "no stock photos of people". Appended in full to every agent prompt. Never summarized,
  never compressed, never retrieved-maybe. This is the actual anti-fade mechanism, and it is small.
- **Embeddings earn their place on the sources, not the goal.** Full DOM plus screenshots of
  several sites genuinely is too big to inject, so retrieve against that. Later, the same applies
  to a blueprint library and past builds across projects. The split: *the goal is small and must be
  complete; the sources are big and can be sampled.*

A memory graph is more defensible than embeddings if relations need modeling — *this section
exists because of that decision* — but for a single site the relation set fits in named JSON
fields. Revisit when a brief change must propagate across a twelve-page site. That is v2.

## 5. Sources

The user supplies reference sites. They are used in **two different roles**, not one pile:

- **One primary reference** — skeleton, rhythm, section order, pacing. Blending six sites yields
  the mean of six sites, which is generic by definition. Design is not additive.

  This was written as intent and then contradicted by the code for months: the sitemap
  came from `commonality.typical_order`, which is literally the mean — conventional
  section types sorted by their average position across sources. Measured: a voice-AI
  agency built from vapi/elevenlabs/kore and a treasury dashboard built from
  ramp/mercury/brex produced the same nine section types in nearly the same order,
  because any two B2B SaaS reference sets average to the same page. The order now comes
  from the primary's own sequence (`rank.primary_order`), including sections unique to
  it; commonality is the checklist only. **When §5 and the code disagree, the code is
  the one that ships.**
- **The rest as a checklist** — what sections exist in this category at all: pricing table, logo
  wall, integration grid, comparison table, FAQ.

Extraction runs through **Playwright** (not Selenium): faster, better screenshot API, and the
accessibility tree is far more useful to a judge model than raw DOM. Both the DOM/a11y structure
and full-page screenshots are captured, so the system sees a site as a user does, not only as
markup.

Sources are then matched against the goal — do these actually serve this brief? — before anything
downstream uses them.

**Legal boundary, to be encoded in system prompts:** extracting structural and layout patterns is
fine. Closely reproducing a specific company's distinctive look for their direct competitor is
not. This distinction belongs in the prompt, not in a policy doc nobody reads.

## 6. Agents

**Design agent.** Looks at sources + goal and proposes a direction: which source skeleton best
aligns with the goal, shown with a snippet of that source, for user approval. Then owns palette,
page count, skeleton, architecture, imagery treatment — what a real designer decides.

**Content agent.** Studies what content the sources use, checks it against the goal, and asks the
user for their real material, showing source snippets as reference for what is being requested.
Generates drafts to react to rather than blank prompts to fill. Keeps provenance: what came from
the user vs. what was drafted.

**Builder agent.** Builds section by section. After building, it visits what it made through the
browser — screenshots, a11y tree, clicking through — and fixes what is broken or off-spec before
moving on. This build → look → fix loop is what pure code-gen misses.

**Observer.** Reviews the full site against goal, approved decisions, and sources. Approves or
rejects with reasons.

### Design authority

**The design agent's output is the source of truth.** There is no external rulebook constraining
what it may propose — that would cap output at the rulebook's taste, and the model is better than
the rulebook. Agents build to the best of model capability given goal and sources.

The distinction that matters: rules **upstream** of the design agent (a rulebook defining good
design) are rejected. The design agent's own recorded decisions **downstream** are not a
constraint system — they are a transcript. The palette, scale, and spacing it chose are written
down so the *builder* is held to them. Not "you must use an 8pt scale" but "you chose these nine
colors; you don't get a tenth at section six."

Without that, "design agent is source of truth" has no enforcement — the builder is a separate
model call that drifts quietly, and the drift shows up as the page falling apart in its lower
third. **Model capability decides what; the recorded decision enforces consistency.**

### Vocabulary open, budget closed

§6 rejected a rulebook of taste. The *schema* then became a rulebook of vocabulary, which
caps output just as hard and more quietly: a designer can only decide what there is a
field for. `DesignSystem` had colours, type, spacing, radii, shadows, motion — and no way
to say "grain over the ground" or "this panel overlaps the one below." Measured on a full
build: zero gradients, zero backdrop blur, zero overlapping elements, on a page built from
sources that use all three — while the scout had already DETECTED ramp's noise layer and
filed it under motion because there was nowhere else to put it. **The pipeline perceived
more than it could express.**

`DesignSystem.treatments` is the open half: `{name, where, how}`, invented per project.
`how` is mandatory and must be implementable as written — "full-bleed" was handed to ten
builders as a word and ten of them returned the default container. A name loses to the
model's prior; classes do not.

Open vocabulary alone produces the opposite failure. Given five treatments and asked to
apply the relevant ones, the builder put a gradient in six sections of ten and repeated
the signature motif down the page. So allocation is a separate, closed decision, made by
the pass that can see the whole page: each section is told which treatments it may use and
whether it carries the signature — exactly one section does. Sections allocated nothing
are told that is deliberate, because a page where every section is treated has no quiet
left in it.

The split to hold onto: **tokens closed and deterministically audited; treatments open and
spot-checked.** They are not equally verifiable and pretending otherwise costs you one or
the other.

### Composition is not the builder's to invent

The builder's prompt said "LAYOUT, COMPOSITION, DENSITY AND RHYTHM ARE YOURS" and, four
lines up, "You do NOT see any other section." Both cannot hold: rhythm is a property
BETWEEN sections. Ten agents deciding shape alone all pick the median — `max-w-6xl` and
`py-24` ten times over. A `compose` stage now decides ground, width and archetype for
every section at once, and the builder is told its shape and its neighbours' by name.
Density and the section's interior stay its own.

Judging follows the same logic: the useful job is catching what the design agent didn't
anticipate — a brand color that kills contrast, content longer than the layout assumed, a mobile
break — not scoring taste. A judge prompted with "is this good design" approves anything on turn
one and nitpicks randomly on turn three.

## 7. Images

The user's real imagery — product and dashboard screenshots — is treated as primary material.

**Regeneration is in scope.** Frontier image models now handle precise UI regeneration well
enough to restyle a raw screenshot to match the winning source's presentation. Practical
safeguard worth building alongside it: a vision diff between original and regenerated version, so
altered numbers, garbled labels, or invented UI surface before the user sees them rather than
after.

**Presentation treatment carries most of the visual quality, independent of regeneration.** What
makes a dashboard shot look designed is the treatment around it: browser chrome or device frame,
perspective tilt, soft shadow, gradient backdrop, bleeding off the right edge, masked fade,
zoomed detail crop with a callout. A vision pass characterizes how the primary source presents
its product imagery; the builder reproduces that treatment. This is CSS/SVG over the asset.

Image generation also covers the layers around the content: backdrops, gradients, texture, spot
illustration, empty-state art, icons. Plus straightforward edits — background removal, upscaling,
recolor of flat illustrations, dark-mode variants.

Two things cheap to build early and painful to retrofit:

- **PII scrub.** Dashboard screenshots are full of real customer names, emails, revenue figures.
  A vision pass that flags and blurs or substitutes them fits the real-content ethos exactly and
  nobody else in this space has it.
- **Asset variants as a first-class blackboard object.** One upload becomes hero-wide,
  card-square, mobile-crop, dark variant. Decide this early or the builder starts stretching
  things.

**Gap case:** a pre-launch user with no product to screenshot. Needs a standing policy — abstract
or illustrative hero rather than a fabricated product shot — decided once, not per run.

## 8. Human interaction

**Three gates, not fifteen.** Brief → design direction → full-page preview. Everything between
runs autonomously. An earlier version of this design had 15+ approval points (skeleton, design,
stack, content, every element, final); nobody finishes that.

**Loops cap at 3 attempts.** Critic-refine plateaus at 2–3 iterations and then oscillates, with
the judge inventing objections to justify its own existence. After 3, stop.

**Escalation is a user-facing choice with concrete options** — not a dump of failed criteria.
"This section can go with a wider hero or a tighter two-column; which do you want?" A business
owner can answer that. `contrast_ratio_failed: 3.9` means nothing to them.

## 9. Stack

Fixed, deliberately. Quality in this category comes precisely from the stack being fixed — the
model never spends reasoning on architecture, and every pattern it generates is one it has seen
ten thousand times.

- **Site output:** Astro or Next, Tailwind, shadcn/ui, one CMS, one form/email provider.
- **Harness:** FastAPI, Postgres (JSONB blackboard), Redis, Docker, job queue.
- **Browser:** Playwright.

**No evolving tech-stack agent.** An agent hunting the newest framework picks something past the
model's cutoff, generates confident wrong code from a docs page, and fails in ways nothing
downstream can diagnose. The modern edge lives in curated, versioned **section blueprints** —
owned, tested, swappable — not in framework selection at runtime.

## 10. v1 vertical slice

One category: B2B SaaS landing pages.

1. Goal elicitation → structured brief JSON
2. One reference URL, manually pasted → Playwright screenshot + section-structure extraction
3. Design agent → design decisions + sitemap → **one human approval**
4. Builder → Astro + Tailwind, section by section from the blueprint library
5. Build → screenshot → review → fix loop
6. Preview URL

Deferred to v2, and only once the simpler version has visibly failed somewhere: multi-agent
coordination, multi-source synthesis, memory graph, multi-page propagation, blueprint retrieval
across past builds.

## 11. Known gaps, measured

Not speculation — each of these was observed on a real build and none is fixed.

- **Every heading is the same sentence.** Seven headings across a page, all paraphrases of
  the offering, two of them byte-identical. The content agent drafts per section from the
  same brief with no knowledge of its siblings, so seven independent calls converge on
  the same claim. Survived four builds and a model upgrade, because it is not a model
  problem: the information never reaches the call. The blackboard already holds every
  drafted headline — it needs projecting into the prompt, not retrieving. Same shape as
  §4's argument: small and complete beats retrieved-maybe.
- **Six of ten sections carry no imagery**, against a category norm of ~12 large images
  per page. The page reads well for one screen and then flattens into type and icon grids.
- **Verify never converges.** Three rounds, then `rounds-exhausted` with NO gate — the run
  stops with nothing a user can answer, which §8 says escalation must never do. The
  proximate cause is image quality: the judge sees a generated dashboard full of garbled
  text, correctly concludes the section is wrong, and its only available fix is to delete
  the image. A guard blocks that, so the rounds burn without progress.
- **The generated imagery is unusable at close range.** `qwen3/pro-text-to-image` renders
  convincing dashboard layouts with gibberish labels. Fine for a POC, fatal for §2's
  real-content thesis. It is one env var (`KIE_IMAGE_MODEL`) — a model choice, not an
  architecture problem. `google/nano-banana` is not an alternative: it refuses bank
  dashboards under Google's prohibited-use policy.
- **Entrance animation played before it could be seen.** 75 `motion.` calls across ten
  sections and zero `whileInView` — everything bound to mount, finished before the reader
  scrolled to it. Fixed in the builder prompt; not yet observed on a build.
- **The stage marker records the stage completed, not the stage entered**, so a run that
  crashes resumes one stage too early and re-opens a gate the user already answered.

## 12. Open questions

- What the content interview actually looks like as an interface. "Asks the user for real content"
  is a UI problem, not an agent problem — a business owner who won't write an About page also
  won't fill in twelve prompts. Voice? A three-question ladder per section with a generated draft
  as the starting point to edit? This is the differentiator and the least designed part.
- Where the primary-reference choice sits: agent-proposed with a snippet for approval (current
  plan) vs. user-picked outright.
- Policy for the pre-launch / no-assets user.
- Where the harness repo lives. This file currently sits in a scratch directory; it belongs at the
  root of the real project, where Claude Code loads it automatically.

## 13. Working preferences

~1 year in voice AI at VoiceOwl. Production multi-agent voice systems, prompt architecture as
state machines, LLM orchestration, tool-invocation discipline. Strong on backend — FastAPI,
Docker, Postgres, Redis. Lighter on frontend and on Git/GitHub; those want step-by-step
walkthroughs rather than assumed familiarity.

Prefers practical, workflow-oriented help over theory.

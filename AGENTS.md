# Agent Specification

> **This is a specification of the agents *this harness runs*.** It is not instructions for a
> coding agent working in this repo — if a tool auto-loads `AGENTS.md` as guidance, that is a
> filename collision, not intent.
>
> Companion to `CLAUDE.md` (architecture context) and `AGENT-RESEARCH.md` (prior art + evidence).
> **Status:** draft 1, for review. Roster is 10 agents + a non-model orchestrator.
> **Last updated:** 2026-08-21

---

## 0. Shared rules

These apply to every agent below and are not repeated in the cards.

**One write path.** `propose_diff` is the only tool that mutates the blackboard. The orchestrator
applies or rejects. No agent writes blackboard state directly — if one can, the versioning is
decorative. Diffs are RFC 6902 JSON Patch (`add` / `remove` / `replace`) against a schema-validated
document; rejections return a reason to the proposing agent so it can adapt.

**Injected, never fetched.** `brief` and `constraints` are injected in full into every agent
prompt. There is no `get_brief` tool, because a fetch is skippable and an injection is not.
Every generation prompt also carries the verbatim fidelity string:

> *Use ONLY the fonts, colors, spacing, and component styles defined in the design system. Do not
> introduce any fonts, colors, or visual styles not in the design system.*

**Deterministic before model.** If it can be computed, compute it. Contrast ratios, computed-style
token extraction, image variant derivation, a11y audit, PII bounding boxes — all deterministic.
Model calls are for judgment only.

**Tools are the permission system.** Boundaries are enforced by withholding capability, not by
prompt instruction. `inspector` and `observer` have no write tools of any kind.

**Loops cap at 3.** Enforced by the orchestrator, not by any agent's own judgment.

**Tool kinds:** `det` deterministic code · `model` LLM/VLM call · `io` browser/fs/network effect ·
`ui` blocks on the user.

## 0.1 Pipeline

```
  router ──► interviewer ──────────────────────────► ┌─ GATE 1: brief ─┐
                  │                                   └────────┬────────┘
             librarian ◄── (any new user statement, any time) ──┤
                                                                ▼
                              scout ──► design_director ──► ┌─ GATE 2: direction + built hero ─┐
                                            │               └────────────────┬─────────────────┘
                        content_editor ◄────┤                                ▼
                             curator   ◄────┘                    builder ⇄ inspector  (≤3)
                                                                            │
                                                                       observer  (≤3)
                                                                            ▼
                                                              ┌─ GATE 3: full preview ─┐
                                                              └────────────────────────┘
```

---

## 1. `router`

**Purpose.** Classify the opening message and choose the entry path. Nothing else.
**Model.** Cheapest available.
**Owns.** `run.entry_path`
**Reads.** The opening message only.

**Tools.** None. Its output is a structured routing decision, not a tool call.

```
{ path: "interview" | "brief_supplied" | "clone_request",
  primary_url: string | null,
  missing: string[] }
```

**Never.** Answer the user's question, generate anything, or paraphrase their words.
**Done when.** A path is set. Single turn, no loop.

> Precedent: Orchids' decision prompt, Kiro's `Mode_Clasifier_Prompt`. Orchids' hard gate is worth
> copying — a clone path requires a clone keyword **and** a concrete URL, else it asks.

---

## 2. `interviewer`

**Purpose.** Turn an open-ended request into a structured brief. Owns **Gate 1**.
**Model.** Mid tier.
**Owns.** `brief` (initial creation only — thereafter `librarian` owns it)
**Reads.** Opening message, router decision.

| Tool | Kind | Notes |
|---|---|---|
| `ask_user(question, chips[], allow_free_text)` | ui | Chips expand into brief fields — the CLAUDE.md §2 autocomplete flow |
| `web_search(query)` | io | Find what the business already has online |
| `fetch_url(url)` | io | Read an existing site / profile the user names |
| `propose_diff` | — | |

**Never.** Ask more than three rounds. Proceed to generation. Ask for something a search could
have found.
**Done when.** `brief` has audience, category, tone, offering, and hard requirements — and the
user has approved it. **Gate 1.**

> Search first, then ask. "I run Acme Plumbing in Leeds" should trigger a lookup, so the first
> question is *"is this still accurate?"* rather than a blank field.

---

## 3. `librarian`

**Purpose.** Keep `brief` and `constraints` correct as the user says new things. Runs on every
new user statement, at any point in the run.
**Model.** Mid tier.
**Owns.** `brief`, `constraints` — **sole writer of both, for the whole run.**
**Reads.** The new statement + current `brief` + current `constraints`.

| Tool | Kind | Notes |
|---|---|---|
| `propose_diff` | — | `add` / `revise` / `supersede`; supersede carries a one-line trace |

**Never.** Search, browse, or read anything but the statement and the current documents.
Paraphrase a hard constraint — user words go into `constraints` verbatim.
**Done when.** The statement is reflected as add, revise, supersede, or explicit no-op.

> Deliberately the most tool-starved agent in the roster. Give it browsing and it will "research"
> a constraint instead of recording it. Verbatim rule is from Orchids: *"Do not rephrase,
> interpret, or modify the user's original words in any way."*

---

## 4. `scout`

**Purpose.** Extract reference sites into usable artifacts, split by role — one primary for
skeleton, the rest as a section checklist.
**Model.** Vision-capable, mid tier (for treatment characterization only).
**Owns.** `sources`
**Reads.** `brief`, reference URLs.

| Tool | Kind | Notes |
|---|---|---|
| `capture_page(url, breakpoints[], scale=2)` | io | Full-page + per-breakpoint. 2x — vision models get materially more signal at 2880px than 1440px |
| `capture_section(url, selector)` | io | Section crops. **Product-critical** — these are the snippets shown at Gate 2 and throughout the content interview |
| `extract_structure(url)` | io+det | a11y tree + DOM → ordered section inventory |
| `extract_tokens(url)` | det | `getComputedStyle` → exact palette, type scale, spacing |
| `extract_brand(url)` | det | Logo, favicon, font families |
| `crawl_links(url, depth=1)` | io | Find the pricing/about pages on checklist sites |
| `characterize_treatment(screenshot)` | model | How this site presents product imagery — frame, tilt, shadow, bleed, crop |
| `propose_diff` | — | |

**Never.** Guess a color from a screenshot when `extract_tokens` can read it. Blend multiple
sources into one structure. Block the run on extraction failure — retry once, then continue
without and say so.
**Done when.** Primary has structure + tokens + screenshots; checklist sites have section
inventories; sources are matched against the brief.

> **Two channels, kept separate.** Computed styles give exact values; vision gives treatment and
> feel. A near-miss hex from a vision model is precisely the drift the design system exists to
> prevent. Budget 60–120s per extraction (Superdesign's observed range).

---

## 5. `design_director`

**Purpose.** Decide the direction: which primary skeleton, the palette, type scale, spacing,
imagery treatment, page count, section order. Owns **Gate 2**.
**Model.** Frontier. This is the agent whose ceiling sets the product's ceiling.
**Owns.** `design_system`, `sitemap`, `sections[].blueprint`, `sections[].ground`
**Reads.** `brief`, `constraints`, `sources`.

| Tool | Kind | Notes |
|---|---|---|
| `read_source_artifact(id)` | det | Tokens, structure, screenshots from `scout` |
| `check_contrast(fg, bg)` | det | WCAG arithmetic — never a model call |
| `render_specimen(palette, type_scale)` | det | Swatch + type specimen card for Gate 2 |
| `list_blueprints(category)` | det | The curated section library |
| `propose_diff` | — | |

**Never.** Specify composition. `design_system` carries **vocabulary** — palette, type scale,
spacing scale, radii, shadows, imagery treatment, motion character. Section layout, density, and
what-goes-where belong to `sitemap` and to the builder. (See `AGENT-RESEARCH.md` §12.)

**One exception, learned the hard way.** Section **ground** (page vs. muted) is a page-level
decision and belongs to `sitemap`. In `experiments/drift-test-01`, pricing and FAQ independently
chose the muted ground, landed adjacent, and merged into one undifferentiated grey block a third
of the page tall. Neither builder could have seen it. Alternation is not a section-local call.
**Done when.** `design_system` + `sitemap` exist, contrast passes, and the user has approved the
direction. **Gate 2.**

**No drawing tool, and no Figma.** Its output is a document, not a picture. Gate 2 shows a *real
built hero* (see §8 note), the primary source snippet, and the specimen — a mockup that doesn't
match the eventual build is worse than none.

---

## 6. `content_editor`

**Purpose.** Get the user's real material into the site, with provenance. The differentiator.
**Model.** Mid–frontier.
**Owns.** `content`
**Reads.** `brief`, `constraints`, `sources`, `sitemap`, `design_system`.

| Tool | Kind | Notes |
|---|---|---|
| `read_source_artifact(id)` | det | What copy do comparable sites use in this section |
| `web_search(query)` | io | Find the user's existing material before asking for it |
| `fetch_url(url)` | io | Old site, Google Business profile, LinkedIn |
| `ask_user_with_reference(question, snippet_image, draft)` | ui | The signature is the point — source snippet **and** a generated draft |
| `propose_diff` | — | Every string carries `provenance: user \| drafted \| adapted` |

**Never.** Present a blank field. Ask for something already findable. Mark a drafted string as
user-supplied.
**Done when.** Every section has content with provenance, and the user has seen every `drafted`
string at least once.

> **Open (CLAUDE.md §11).** The interview interface is still undesigned. Current bet: search
> first, draft from what's found, ask the user to *correct* rather than compose. A business owner
> who won't write an About page will readily fix one.

---

## 7. `curator`

**Purpose.** Turn uploaded material into safe, correctly-shaped assets.
**Model.** Vision, mid tier.
**Owns.** `assets`
**Reads.** `brief`, `constraints`, `design_system` (for treatment + dark variants).

| Tool | Kind | Notes |
|---|---|---|
| `ingest_asset(file)` | det | |
| `detect_pii(image)` | det | OCR + NER (GLiNER / OpenAI Privacy Filter) → bounding boxes |
| `redact_region(asset, box, mode)` | det | Blur or substitute |
| `derive_variants(asset)` | det | hero-wide, card-square, mobile-crop, dark |
| `remove_background`, `upscale`, `recolor` | det | |
| `generate_image(prompt, refs[])` | model | Backdrops, texture, spot illustration, empty-state art |
| `edit_image(asset, instruction)` | model | Includes UI regeneration to match source treatment |
| `vision_diff(original, regenerated)` | model | Flags altered numbers, garbled labels, invented UI |
| `propose_diff` | — | |

**Never.** Publish a regenerated asset that failed `vision_diff`. Ship an un-scanned screenshot.
Fabricate a product shot for a pre-launch user — **standing policy: abstract or illustrative hero
instead** (CLAUDE.md §7 gap case).
**Done when.** Every asset is PII-clean, has its variants, and any regeneration has passed diff.

> **Review question:** this is ten tools and two risk profiles. Case for splitting `curator`
> (PII + variants, all deterministic, pass/fail) from an `illustrator` (generation + regeneration,
> all model, creative). See §11.

---

## 8. `builder`

**Purpose.** Build the site section by section, to the recorded design decisions.
**Model.** Frontier.
**Owns.** `sections[].build_status`. Files on disk — **not** in the blackboard.
**Reads.** Everything. `design_system` + `constraints` + fidelity string injected on every call.

| Tool | Kind | Notes |
|---|---|---|
| `read_file`, `list_dir`, `grep`, `glob` | io | |
| `edit_file(path, search, replace)` | io | **Preferred.** Lovable and Orchids both mandate search-replace over rewrites |
| `write_file(path, content)` | io | New files and full rewrites only |
| `run_command(cmd)` | io | Scoped allowlist: install, build, dev. Background anything over ~2 min |
| `read_blueprint(id)` | det | Curated section library |
| `propose_diff` | — | Includes **design-system extension requests** — see below |

**Never.** Introduce a font, color, spacing value, radius, or shadow not in `design_system`.
Write ad-hoc styles in a component when a token exists. Mark a section complete without
`inspector` clearing it.

**May.** Change layout, structure, composition, density, rhythm, responsive behavior,
interaction — freely. That is the creative surface and it is not constrained.

**Design-system extension.** When a section genuinely needs vocabulary that doesn't exist, the
builder emits a diff against `design_system` and continues once applied. It is not forbidden from
needing a tenth color; it is forbidden from taking one silently. Three extension requests across
three sections is a signal the direction was wrong — surface it, don't absorb it.

**Done when.** Section renders, `inspector` reports no defects, status is `built`.

---

## 9. `inspector`

**Purpose.** Look at what was built and report what's wrong. Cannot fix.
**Model.** Vision, mid tier.
**Owns.** Nothing.
**Reads.** `design_system`, `constraints`, `sections[]`, the running preview.

| Tool | Kind | Notes |
|---|---|---|
| `screenshot(breakpoints[], scale=2)` | io | **Must scroll the full page first** — `whileInView` entrance animations start at `opacity: 0` and never fire under a non-scrolling `fullPage` capture, so every below-fold section reads as empty. Confirmed in `experiments/drift-test-01` |
| `get_a11y_tree()` | io | |
| `click`, `fill`, `scroll` | io | Interaction, not just static capture |
| `read_console()`, `read_network()` | io | Lovable mandates debugging tools *before* reading code |
| `run_axe()` | det | Deterministic a11y audit |
| `check_contrast(fg, bg)` | det | |
| `report_defects(defects[])` | — | Structured, not prose |

**Never.** Edit anything. Score taste. Report a defect it cannot point at with a selector,
screenshot region, or console line.
**Done when.** Defect list emitted — possibly empty.

> Split from `builder` deliberately, following Emergent (`auto_frontend_testing_agent` is a
> separate subagent even though the main agent can drive a browser). Sharing a context window with
> the thing that wrote the code means grading its own homework.

---

## 10. `observer`

**Purpose.** Final pass over the whole site. Approve or reject with reasons.
**Model.** Frontier, vision.
**Owns.** Nothing.
**Reads.** Everything, plus full-page screenshots at every breakpoint.

| Tool | Kind | Notes |
|---|---|---|
| `read_blackboard()` | det | |
| `read_screenshots()` | det | Full page, all breakpoints |
| `compare_to_source(primary)` | model | Against the primary reference, on structure — not pixels |
| `check_constraint(id)` | det+model | "no blue" is a palette sample, not an opinion |
| `report_verdict(approve \| reject, reasons[])` | — | Every reason cites a `constraint.id` or `decision.id` |

**Never.** Edit. Score "is this good design" — a judge given that prompt approves on turn one and
nitpicks on turn three (`AGENT-RESEARCH.md` §8). Reject without citing a named constraint or
recorded decision.

**Scope.** Only what `design_director` could not have anticipated: a brand color that kills
contrast in context, content longer than the layout assumed, a mobile break, cross-section
inconsistency.
**Done when.** Verdict emitted. **Gate 3** on approve.

---

## 11. Orchestrator (not an agent)

Deterministic code. Applies or rejects diffs against the schema; returns rejection reasons;
appends to `decisions`; counts attempts and enforces the 3-cap; sequences the pipeline; owns the
three gates.

**One model call it does own:** escalation phrasing. Turning `contrast_ratio_failed: 3.9` into
*"This section can go with a wider hero or a tighter two-column — which do you want?"* is a
language task (CLAUDE.md §8).

## 12. Deliberately not agents

| Thing | Why not | Where it lives |
|---|---|---|
| Deploy / preview URL | Deterministic build + push | Orchestrator |
| SEO | A checklist, not a judgment. Lovable does it inline | `builder` prompt |
| Blueprint selection | A decision, and the design agent already owns decisions | `design_director` |
| Lint / typecheck / build errors | Deterministic; run before any model sees the page | Orchestrator, pre-`inspector` |
| Tech stack choice | Fixed by design (CLAUDE.md §9) | — |
| Support / help / billing Q&A | Real (Emergent ships one) but out of v1 scope | v2 |
| Copy QA, brand voice | Folded in | `observer` |

## 13. Open for review

1. **Split `curator`?** Ten tools, two risk profiles — deterministic safety work vs. creative
   generation. Splitting gives `illustrator` its own creative context; keeping them together
   means one agent owns "the asset" end to end.
2. **Does `interviewer` survive Gate 1?** It only ever runs once. Arguably it is `librarian` with
   a different prompt and a `ask_user` tool. Merging drops the roster to 9.
3. **Is `router` worth a call?** It saves a frontier call on every run, but adds a hop. Could be a
   classifier head on `interviewer` instead.
4. **`content_editor` before or after `design_director`?** Currently after, so drafts can be
   written to a known layout. The reverse means design knows the real content length — which is one
   of the defects `observer` exists to catch.
5. **v1 slice is B2B SaaS landing pages.** Which of these 10 are actually needed for that?
   Plausibly: router, interviewer, scout, design_director, builder, inspector. Five deferred.

---

## 14. Locked stack

Decided 2026-08-21. Supersedes the Astro suggestion in `AGENT-RESEARCH.md` — that optimized for
blueprint cleanliness over output quality, which is the wrong trade for this product.

### The stack

| Layer | Choice | Pin |
|---|---|---|
| Framework | **Next.js 16.3.1**, App Router, `output: "export"` | SSG output — SEO works, which is non-negotiable for business sites |
| Language | **TypeScript 5.9.3**, React 19.2.8 | |
| CSS | **Tailwind 4.3.3**, CSS-first `@theme`, **OKLCH** tokens | Not v3. See below — this one matters more than it looks |
| Components | **shadcn/ui** — radix base, nova preset | Radix over Base UI: the most-trodden path is the point. Nova ships Lucide + Geist |
| Animation | **Motion 13.1.1** | Package is `motion`, import from `motion/react` — **never `framer-motion`** |
| Icons | **lucide-react 1.33** | Never emoji as icons |
| Images | pre-sized variants from `curator` | `images.unoptimized` — static export has no runtime optimizer |
| Package manager | **pnpm 11.22** | Not for speed — see §15 |

Built and verified in `scaffold/`. `pnpm build` reaches *prerendered as static content*.

### Why this, on evidence

- **[UI-Bench](https://arxiv.org/abs/2508.20410)** (10 tools, 30 prompts, 300 sites, 4,075 blinded
  expert pairwise judgments, TrueSkill): **Orchids ranks #1** — 30.12 mean rating, 67.5% win rate —
  ahead of Figma Make (27.46, 57.1%) and Lovable (27.14, 54.8%). Orchids runs Next.js App Router +
  Tailwind + shadcn, and its full system prompt is in the corpus.
- **Lovable's cited strength is Framer Motion + high-end typography.** Motion is not decoration;
  it is what expert judges register as design quality.
- **v0 is cited as best-in-class for "React + Next.js + shadcn/ui design fidelity."**
- Next 16 + React 19 + TS 5 + Tailwind v4 + shadcn is the current standard production combination;
  premium landing templates converge on App Router + static export + Tailwind v4 + OKLCH tokens.

### Why Tailwind v4 specifically

This is load-bearing for the design-system enforcement in §5 and §8, not a version bump.

1. **CSS-first `@theme` means the design system *is* a CSS file the model reads natively.** Agents
   parse CSS custom properties reliably and JS config files unreliably.
2. **It structurally eliminates a documented failure.** Lovable's leaked prompt carries a
   `CRITICAL COLOR FUNCTION MATCHING` warning about HSL/RGB mismatch between `index.css` and
   `tailwind.config.ts` producing wrong colors. That bug is a v3 artifact of having two config
   surfaces. v4 has one.
3. **OKLCH is perceptually uniform** — equal numeric change produces equal visual change. For a
   `design_director` generating palettes programmatically and running `check_contrast`, scales
   behave predictably instead of needing per-hue correction.

### Why not Figma Make, despite ranking #2

Figma Make is a strong closed product, not a callable component. Routing the design step through
it hands the core differentiator to a tool that never sees the brief, the constraints, or the
sources. Note also what the benchmark actually shows: **Orchids beat Figma Make** — a
design-system-document-then-code pipeline beat a design-tool-then-export pipeline. That is direct
support for the CLAUDE.md §6 architecture.

Figma MCP stays legitimate in the reverse direction: a user who *arrives with* a Figma file. A v2
input source for `scout`, not a design tool.

### Starter ban list

Written as capability boundaries, following Lovable's *"it is not possible"* framing rather than
"prefer". Grows as things break.

- Not possible: Vue, Svelte, Angular, Astro, plain CRA, or any framework swap
- `framer-motion` — the package is `motion`, imported from `motion/react`
- styled-jsx, CSS-in-JS of any kind, `.module.css` — Tailwind only
- `tailwind.config.js` colors — tokens live in `@theme` in the CSS file
- Direct color utilities in `className` (`text-white`, `bg-black`) — semantic tokens only
- Emoji as icons; hand-drawn SVG paths for maps; gradient blobs as filler
- `transition: all` — breaks transforms
- Hand-editing `package.json` or the lockfile — `pnpm add` only
- Rewriting a manifest wholesale rather than amending it

## 15. Dependency tiers

The foundation is locked; leaves are open and **recorded**. This is not the "evolving tech-stack
agent" CLAUDE.md §9 rejects — that is runtime *architecture* selection. This is runtime *library*
selection against a fixed architecture.

| Tier | Contents | Rule |
|---|---|---|
| **Foundation** | §14 table | Locked. Change requests refused as a capability boundary |
| **Blessed** | shadcn, Motion, lucide, sharp | Pre-installed in the template. No gate |
| **On-demand** | carousel, charts, maps, lottie, … | Must pass the gate, then registered |

**Why pnpm, specifically.** Not speed — **hardlinking**. pnpm resolves into a global
content-addressable store and hardlinks into each project's `node_modules`, so per-project
isolation stops being expensive: the hundredth project costs seconds and near-zero disk, while
the lockfile guarantees byte-identical versions. This is what makes the scaffold source-only.
`node_modules` is never committed and **never copied per project** — copying it would cost
~550MB per site. Copy the source (~200KB), then `pnpm install --frozen-lockfile`.

**`dependencies` is a first-class blackboard object**, injected into every builder call, mutated
only by diff — exactly like `design_system`, and for the same reason. Without it, the builder
hand-rolls a carousel at section 6 that section 2 already installed embla for. Same failure as the
tenth color; same fix.

**The gate** — steps 2–4 are `pnpm` plus a build, not model calls:

1. **Already solved?** Check `dependencies`, blessed tier, shadcn registry. Biggest source of bloat.
2. **Real and current?** Resolve against npm — catches hallucinated names and 2023 abandonware.
3. **Installs clean?** `pnpm add --dry-run` against the real lockfile — catches React 19 / Next 16
   peer conflicts.
4. **Build still passes?** Install, build.
5. **Config recorded.** Tailwind plugin, `transpilePackages`, provider in layout — stored with the
   dependency so the next agent doesn't rediscover it.
6. **Client or server** — recorded, not re-derived.
7. **Bundle cost.** 300kb for one animation is a bad trade on a landing page. The only judgment step.

Builder proposes, orchestrator verifies, blackboard records.

## 16. Benchmarks to track

| Benchmark | What it measures | Why it matters here |
|---|---|---|
| [**UI-Bench**](https://arxiv.org/abs/2508.20410) (uibench.ai/leaderboard) | Expert blinded pairwise design quality across text-to-app tools, TrueSkill | The only design-quality benchmark for this exact product category. This is the number to beat |
| **WebDev Arena** | Human-voted head-to-head frontend generation, Elo | Aug 2026: Claude Opus 5 leads at 1691, Kimi K3 1674, Grok 4.6 1630 — 596k votes / 117 models. Model selection for `builder` |
| **Arena Image-to-WebDev** | Screenshot → site | Directly the `scout` → `builder` path. Anthropic models hold #1–3 |
| [WebDevJudge](https://arxiv.org/html/2510.18560v1) | LLM-as-judge reliability for web dev | Calibrating `observer` |
| [Design2Code](https://salt-nlp.github.io/Design2Code/) | Screenshot → code fidelity, 484 pages | Regression testing extraction fidelity |

**Steal UI-Bench's judging frame for `observer`.** It anchors evaluation as *a client-delivery
question* — would you ship this to the client — rather than "is this good design." That is a
concrete answer to the CLAUDE.md §6 worry that a taste-prompted judge approves on turn one and
nitpicks on turn three, and it is the frame that produced 4,000 usable expert judgments.

# Agent Architecture — Prior Art Research

> Companion to CLAUDE.md. Evidence gathered 2026-08-21 from leaked production system
> prompts and open-source projects. **This is research, not a spec.** Section 7 proposes
> a roster; everything before it is what other people actually shipped.

**Local corpus** (cloned, readable offline):
- `…/scratchpad/spa/` — [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) — 30 vendors incl. Lovable, Emergent, Orchids.app, v0, Bolt, Replit, Same.dev, Leap.new, Kiro, Devin, Manus
- `…/scratchpad/sds/` — [superdesigndev/superdesign-skill](https://github.com/superdesigndev/superdesign-skill) — the most complete open design-agent SOP found

---

## 1. Headline finding: nobody in this category runs an agent mesh

Every shipped competitor is **one driver agent plus specialists exposed as tools**. Not one
is a peer network, and not one is a blackboard.

| Product | Shape | Agent roster |
|---|---|---|
| **Lovable** | Single agent, ~300 lines, no subagents | — |
| **Orchids.app** | 3-stage pipeline + tool-subagents | router → `generate_design_system` → `handoff_to_coding_agent`; then `use_database_agent`, `use_auth_agent`, `use_payments_agent` |
| **Emergent** | Main agent + 6 tool-subagents | `vision_expert_agent`, `auto_frontend_testing_agent`, `deep_testing_backend_v2`, `integration_playbook_expert_v2`, `support_agent`, `deployment_agent` |
| **v0** | Single agent + design tools + memories | `GenerateDesignInspiration`, `Inspect Site` |
| **Replit** | Assistant + "workspace tool nudges" | routes to Secrets/Deployments surfaces, not agents |
| **Kiro** | Classifier in front | `Mode_Clasifier_Prompt` → `Spec_Prompt` \| `Vibe_Prompt` |

**What this means for the blackboard.** The no-A2A instinct in CLAUDE.md §3 is correct and
universally confirmed. But the industry's answer is *orchestrator-with-tool-subagents*, which is
strictly simpler than a versioned blackboard. The blackboard is therefore a genuine
differentiator **and** the largest unvalidated bet in the design. It has academic backing
(§6) but no product proof.

## 2. The delegation contract — steal this shape verbatim

Orchids' `use_database_agent` block is the best-written subagent boundary in the corpus. The
pattern, generalised:

```
1. WHEN:      "You MUST use this tool when: <triggers>"
2. OWNS:      "<Agent> Responsibilities:" — explicit file paths it alone may write
3. FORBIDS:   "You MUST NEVER handle any of the following:" — mirror of the OWNS list
4. WORKFLOW:  read current state → construct a plan → call agent WITH that plan
              → agent returns an INTERFACE → caller integrates it
5. NO-REDO:   "This tool already installs deps and sets up env vars.
               No need to call npm_install."
```

Two details worth copying:
- **File-path ownership, not topic ownership.** "Never edit `src/db/schema.ts` on your own"
  is enforceable. "Handle database concerns" is not.
- **The caller sends a plan, the subagent returns an interface.** The parent reads the codebase,
  decides what's needed, and the subagent hands back API endpoints the parent then wires into UI.
  Applied here: the design agent returns a design system the builder consumes — never a
  free-form conversation.

**Emergent's warning, verbatim:** *"Subagent sometimes is dull and lazy so doesn't do full work
or sometimes is over enthusiastic and does more work. Please check the response from sub agent
including git-diff carefully."* Their mitigation is a diff review of every subagent return. This
is an independent argument for diff-based state: it is what Emergent bolted on after the fact.

## 3. The design stage is separate, upstream, and produces a durable artifact

Universal across the corpus — and it matches CLAUDE.md §6 exactly.

- **Orchids**: `generate_design_system` runs *before* any code exists. Its output is handed
  to the coding agent. The router is forbidden from calling it in parallel with `clone_website`
  — strictly sequential.
- **Superdesign**: writes `.superdesign/design-system.md` covering *product context, key pages
  & architecture, JTBD, color/font/spacing/shadow/layout, motion patterns, project requirements*.
  Plus six repo-analysis files: `components.md`, `layouts.md`, `routes.md`, `theme.md`,
  `pages.md`, `extractable-components.md`.
- **Lovable**: the design system *is* `index.css` + `tailwind.config.ts`. Components may never
  carry ad-hoc styles — enforcement by making the token file the only legal place for a color.

### The enforcement mechanism you are missing

Superdesign's `DESIGN SYSTEM FIDELITY` section is CLAUDE.md §6 arrived at independently, with
the mechanism spelled out:

> "Without explicit constraints, the design agent will invent random fonts (serif, decorative),
> random colors (pink, neon, purple gradients), and random button styles… The design system is a
> **hard constraint, not a suggestion**: iteration prompts explore layout/structure/content
> direction, **never visual style**."

Their three enforcement rules:
1. Pass `design-system.md` as `--context-file` on **every** generation call
2. Pass the token file (`globals.css`) on **every** call
3. **Append a fidelity string to every prompt**: *"Use ONLY the fonts, colors, spacing, and
   component styles defined in the design system. Do not introduce any fonts, colors, or visual
   styles not in the design system."*

Rule 3 is structurally identical to CLAUDE.md §4's verbatim hard-constraint list. Same
anti-fade mechanism, same reasoning, already validated in production. **The split that makes it
work: iteration prompts may change layout/structure/content; they may never change visual
style.** That is the concrete version of "you don't get a tenth color at section six."

## 4. Everyone ships a design rulebook — but it is a ban list, not a taste rubric

CLAUDE.md §6 rejects "rules upstream of the design agent." The corpus disagrees — *but* every
shipped rule is a **negative constraint**, never a positive definition of good design. That is
the reconciliation: ban known failure modes, don't define taste.

**v0** — `## Color System`, `## Typography`, `## Visual Elements & Icons`:
- exactly 3–5 colors total; 1 primary + 2–3 neutrals + 1–2 accents; never exceed 5
- **never use purple or violet prominently** unless asked
- avoid gradients entirely unless asked; if needed, analogous only (blue→teal), never
  opposing temperatures (pink→green), max 2–3 stops
- max 2 font families, ever; line-height 1.4–1.6 for body
- override a background color → you MUST override its text color
- never emojis as icons; never generate gradient blobs/blurry squares as filler
- never hand-draw SVG paths for maps — use a mapping library
- closing line: *"Ship something interesting rather than boring, but never ugly."*

**Emergent** — the `80/20 GRADIENT RESTRICTION RULE`:
- gradients on ≤20% of visible page area, hero/section backgrounds only
- never dark purple/pink gradients on buttons; never gradients on elements <100px wide
- never gradients on text/reading areas; never layer two gradients in one viewport
- **enforcement clause**: if gradient area >20% OR affects readability, downgrade to a
  two-color same-hue gradient or a solid
- no `transition: all` (breaks transforms); no `.App { text-align: center }`
- never system-UI font; never "typical basic red blue green"; icons from lucide-react only

**Lovable**: never `text-white`/`bg-white` in a `className`; semantic tokens only; HSL only in
`index.css`; explicitly warns the model about its own recurring bug — *"You often make mistakes
having white text on white background."*

The convergence on **"not purple/violet"** across three independent vendors is the single most
telling data point in the corpus: it is a documented model failure mode, not an aesthetic
opinion. A ban list of ~15 such items costs nothing and caps nothing.

## 5. Source extraction — the primary/checklist split already exists

**Superdesign `extract-website`** produces, per flag:
- `--design-md` → `design.md`, a portable style guide
- `--content-structure` → `content-structure.md`, section/page structure
- `--tokens` → `tokens.json`
- `--brand` → `brand.json` (logo, colors, fonts)
- `--clone` → static `clone/index.html`, explicitly *"a visual reference to look at while you
  build. It is NOT editable and NOT a generation input."*

Their restyle recipe is CLAUDE.md §5 formalised: **extract `--content-structure` from the
CONTENT site and `--design-md` from the STYLE site.** Structure from one source, aesthetic from
another — which is exactly "one primary reference for skeleton, the rest as checklist," and it
confirms the anti-blending argument.

Three more things worth taking:
- **Merging is supported but framed as a distinct, explicit mode** (`merge stripe.com and
  vercel.com`), never the default.
- **Legal framing, ready to lift**: *"The result is a style-informed rebuild, not a pixel copy."*
  Says the CLAUDE.md §5 boundary in seven words.
- **Timeout reality**: extraction *"can take ~60–120s"*, retry once, then offer to continue
  without it rather than blocking. Budget for this in the job queue.

**Orchids' router** gates cloning hard: the request must contain a clone keyword *and* a
concrete URL, else it asks. And it must pass **the exact unmodified user request** downstream —
*"Do not rephrase, interpret, or modify the user's original words in any way."* That is a
provenance rule, and it belongs on the librarian.

**Open-source implementation**: [firecrawl/open-lovable](https://github.com/firecrawl/open-lovable)
(~26.7k stars) — URL → React via Firecrawl scrape + LLM + E2B/Vercel sandbox. The reference
implementation for the whole extract→generate path, MIT-ish and readable.

## 6. Blackboard: the academic backing you didn't have

- **PatchBoard** ([arXiv 2605.29313](https://arxiv.org/pdf/2605.29313)) — *Schema-Grounded State
  Mutation for Reliable and Auditable LLM Multi-Agent Collaboration.* Agents propose **JSON Patch
  (RFC 6902)** operations (`add`/`remove`/`replace`) against shared JSON state. A validation layer
  checks each patch against a schema, **rejects invalid ones and returns the rejection reason to
  the agent so it can adapt**. Full attribution and reversibility. This is the CLAUDE.md §3
  blackboard with a citable wire format — use RFC 6902 rather than inventing a diff shape, and
  feed rejection reasons back rather than silently dropping.
- **Blackboard for information discovery** ([arXiv 2510.01285](https://arxiv.org/abs/2510.01285))
  — reports **13–57% relative improvement in end-to-end task success** over centralized-orchestrator
  and master-slave baselines. Note their variant lets subagents *volunteer*; the harness design
  deliberately does not, which is the right call for a bounded pipeline.
- **MetaGPT** ([arXiv 2308.00352](https://arxiv.org/abs/2308.00352), ICLR 2024 oral) — SOPs encoded
  as prompt sequences, roles (PM/Architect/Engineer/QA) forced to emit **standardized deliverables
  (PRD, API design) that are strict inputs to the next agent**. The formal name for what
  brief → design_system → sitemap → sections is.

## 7. Context-fade evidence

Emergent's prompt states it outright: *"Only last 10 messages have full observations, rest are
truncated once the history is very long — so important things must be repeated in thoughts as
plans or checklist or phases and must be **repeated periodically**."*

That is a production system confirming CLAUDE.md §4's premise, and its fix is repetition of a
small structured document — not retrieval. **v0** independently ships a `# Memories` section with
`### When to save memories` / `### When NOT to save memories` rules, which is the librarian's
job description. Neither uses embeddings for goal state.

## 8. Verification loop

- **Emergent** splits verification into two subagents: `auto_frontend_testing_agent` (Playwright
  + browser automation) and `deep_testing_backend_v2` (curl + Playwright). Verification is a
  *different agent* from the builder, even though the builder can drive a browser.
- **GUI-GENESIS** ([arXiv 2602.14093](https://arxiv.org/pdf/2602.14093)) — two-stage verification
  with **K=5 retries**; generates a companion Playwright script that must execute the golden path.
  CLAUDE.md's cap of 3 is in the right zone, slightly tighter.
- **WebDevJudge** ([arXiv 2510.18560](https://arxiv.org/html/2510.18560v1)) — benchmarks
  (M)LLM-as-judge for web development quality and finds reliability in open-ended dynamic
  evaluation unproven. Direct evidence for §6's "a judge prompted with *is this good design*
  approves anything on turn one."
- **Design2Code** ([salt-nlp.github.io/Design2Code](https://salt-nlp.github.io/Design2Code/)) and
  **UI-Bench** ([arXiv 2508.20410](https://arxiv.org/pdf/2508.20410)) — existing benchmarks if the
  observer ever needs calibrating against something other than its own opinion.
- **Resolution matters**: a vision model gets materially more signal from a 2880px screenshot than
  a 1440px one. Set the Playwright device scale factor accordingly.

## 9. Best open-source per role

| Role | Best reference | Why |
|---|---|---|
| **Design** | [superdesign-skill](https://github.com/superdesigndev/superdesign-skill) | Only complete design-agent SOP found: design-system.md contract, fidelity enforcement, website extraction, iteration-mode routing, warm/cold resume. Read `references/SUPERDESIGN.md` first. |
| **Design (tokens/components)** | [marvkr/better-design](https://github.com/marvkr/better-design) | MCP server + shadcn registry, 31 brand-grade themes (Linear/Stripe/Vercel/Notion…), semantic tokens + real component code, `get-review-rules` returns a WCAG + visual checklist. Closest thing to a shippable observer rubric. |
| **Design (agent-agnostic runtime)** | [nexu-io/open-design](https://github.com/nexu-io/open-design) | `DESIGN.md` as "the core brand contract"; pipeline *"discover the brief, lock the direction, stream the artifact, critique, deliver"* — the same five stages, four planes (plugins / skills / templates / design systems). |
| **Constrained UI output** | [thesysdev/openui](https://github.com/thesysdev/openui) | Generative-UI standard: Zod-schema component library → system prompt generated *from* the library → model can only emit registered components. The formal version of a section blueprint library. |
| **Extraction → build** | [firecrawl/open-lovable](https://github.com/firecrawl/open-lovable) | Working URL → React pipeline, ~26.7k stars. |
| **Prompt corpus** | [x1xhlol/…ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | Already cloned. Emergent and Orchids are the two closest analogues to this project. |
| **PII scrub** | OpenAI Privacy Filter (Apache 2.0, local, 8 PII categories) + [GLiNER](https://github.com/urchade/GLiNER) zero-shot NER; [ScreenLeak](https://screenpipe.github.io/screenleak/) is a screenshot-PII benchmark | §7's PII pass — OCR + NER over the screenshot beats asking a vision model to "find PII". |
| **Brief elicitation** | AWS Kiro (`Spec_Prompt.txt` in the corpus), GitHub Spec Kit, EARS notation | Kiro splits into user stories + acceptance criteria in EARS: *"WHEN [trigger], THE [system] SHALL [response]"*. A testable format for `brief.hard_requirements`. |
| **Blackboard** | PatchBoard (RFC 6902 + schema validation + rejection reasons) | §6 above. |

## 10. Proposed roster

Keeps the CLAUDE.md §6 names; adds what the corpus says is missing. Naming convention: agents are
**roles**, tools are **verbs**.

**Front of pipeline**
1. `router` — *new, from Orchids/Kiro.* Cheap model, one job: classify the opening message into
   `interview` / `brief_supplied` / `clone_request`, and refuse to proceed on a clone request with
   no concrete URL. Never writes to the blackboard beyond setting the entry path.
2. `interviewer` — owns goal elicitation → `brief`. Autocomplete chips expand into structured
   fields. **Gate 1** at its exit.
3. `librarian` — owns `brief` + `constraints` for the whole run. Only agent permitted to write
   either. Emits add/revise/supersede diffs. Inherits Orchids' verbatim rule: user words are
   preserved exactly in `constraints`, never paraphrased.

**Materials**
4. `scout` — owns `sources`. Playwright extraction, split by role: structure from the primary,
   section-inventory checklist from the rest. Emits `design.md`-equivalent, `content-structure`,
   `tokens.json`, screenshots, a11y tree. Retry once on timeout, then continue without.
5. `curator` — *new.* Owns `assets`. PII scrub, variant derivation (hero-wide / card-square /
   mobile-crop / dark), vision-diff on any regenerated image. Split out from the builder because
   §7's safeguards are pass/fail checks, not creative work, and shouldn't share a context window
   with layout decisions.

**Direction**
6. `design_director` (CLAUDE.md's design agent) — owns `design_system` + `sitemap`. Consumes
   brief + sources, proposes one primary skeleton with a snippet. Output is a document, and that
   document is injected into every downstream call. **Gate 2** at its exit.
7. `content_editor` (content agent) — owns `content`. Provenance flag on every string.
   Interview UI remains the open question (CLAUDE.md §11).

**Execution**
8. `builder` — owns `sections[].build`. One section at a time. Receives design_system +
   constraints + the fidelity string on every call. May change layout/structure/content; may
   never introduce a visual style not in `design_system`.
9. `inspector` — *split out from the builder, per Emergent.* Screenshots at 2x, reads the a11y
   tree, clicks through, and reports defects. Cannot edit. Keeping it separate stops the builder
   from grading its own homework in the same context window.
10. `observer` — final pass against brief + decisions + sources. Scoped to what the design
    director could not have anticipated: contrast failures, content overflow, mobile breaks.
    Not taste. Rejections must cite a constraint or a recorded decision by name.

**Not agents** — orchestrator (applies/rejects diffs, owns the 3-attempt cap and escalation),
blueprint library (data), token/lint checks (deterministic code, run before any model sees the page).

## 11. What the corpus argues against in the current design

1. **§6 "no rulebook upstream of the design agent" is too strong.** Every shipped product has one.
   Adopt a ~15-line **ban list** (§4 above) — negative constraints only, no taste definitions.
   It costs nothing and prevents the specific failures three vendors independently documented.
   See §12 for how "hard constraint" is reconciled with builder agency.
2. **The blackboard has no product precedent.** Orchids and Emergent both ship with a plain
   orchestrator plus tool-subagents. Ship the v1 slice that way and let the blackboard earn its
   place — or accept it as the deliberate bet and use RFC 6902 so at least the wire format is
   standard.
3. **`inspector` should be separate from `builder`.** Emergent, the closest analogue, splits it.
4. **Section blueprints want a schema, not a folder.** OpenUI's Zod-registry → generated system
   prompt is the mechanism that makes "the builder may only use blueprint sections" enforceable
   rather than aspirational.

---

## 12. Design authority: constraint vs. feedback — resolved

The objection to §3's "hard constraint" framing: freezing the design system removes the
builder's agency and makes the design agent the sole author. That is correct **only if the
design system specifies composition**. It does not follow if it specifies vocabulary.

**Frozen (vocabulary):** palette, type scale, spacing scale, radii, shadow set, imagery
treatment, motion character. Roughly forty tokens.

**State every scale as a closed enumeration.** `experiments/drift-test-01` measured this
directly across five independent builds. Rules written as closed sets with the boundary spelled
out — *"Nine values. There is no tenth."*, *"weights 400/500/600 only, never 700 or above"* —
held perfectly. Rules written as an open scale leaked: *"Grid gap `gap-8`"* never addressed
inline flex gaps, so agents invented `gap-2`, `gap-3`, `gap-4`. **A scale with an unstated
boundary is an invitation.**

**Never frozen (composition):** section layout, visual rhythm, hierarchy, density, what bleeds
off which edge, responsive behavior, interaction, how a screenshot is framed. This is the
majority of what makes a page look designed, and it stays with the builder.

**Why feedback-only fails specifically.** An observer reviewing section 6 sees a fine section.
Section 1 was also fine. What is broken is that they *disagree with each other*, and a reviewer
working section-by-section structurally cannot see disagreement. By the time the whole page is
in view it is a rewrite, not feedback. This is CLAUDE.md §6's "falling apart in its lower third",
and it is also why feedback-only burns the entire 3-loop budget on a class of defect that a
forty-token document prevents from existing — budget that should go to the unanticipated:
contrast failures, content overflow, mobile breaks.

**The resolution — the builder proposes design-system diffs.** The builder is not forbidden from
needing a tenth color; it is forbidden from *taking* one silently. It emits a diff against
`design_system`, and the orchestrator applies or rejects it. This preserves agency, allows the
design direction to be wrong without being fatal, and keeps the transcript intact.

It also produces a signal worth having: three palette-extension requests across three sections
means the design direction was wrong. Better to learn that than to absorb it one hex code at a time.

> **Hard constraint is not "you may not have a tenth color." It is "you may not have a tenth
> color that nobody wrote down."**

---

## 13. Tool inventory per agent

### Three cross-cutting rules

**1. One write path.** `propose_diff` is the only tool that mutates the blackboard, and only the
orchestrator applies. Every other tool either reads state or has an effect in the world (browser,
filesystem, image). If any agent can write blackboard state directly, the blackboard is decorative.

**2. Deterministic before model.** Contrast ratios, computed-style token extraction, image variant
derivation, a11y audit, PII bounding boxes — compute these. A model asked for a contrast ratio is
doing arithmetic badly and expensively. Reserve model calls for judgment. This is where most
harnesses waste their budget.

**3. Tools are the permission system, not the prompt.** Orchids enforces its subagent boundaries in
prose — *"NEVER edit `src/db/schema.ts` on your own"* — because it cannot do it structurally. This
harness can: `inspector` and `observer` are given no write tools at all. A capability the agent
does not have cannot be prompted away.

Also worth copying from Orchids: an explicit **parallelization declaration** per tool. It lists
which may run concurrently and names the two that never may (`edit_file`, `todo_write`).

### Per-agent

| Agent | Tools | Notes |
|---|---|---|
| `router` | *(none)* | Output is a structured routing decision, not a tool call. Cheapest model. |
| `interviewer` | `ask_user(question, options[], allow_free_text)`, `web_search`, `fetch_url`, `propose_diff` | Search matters: "I run Acme Plumbing in Leeds" → find what already exists before asking. |
| `librarian` | `read_blackboard`, `propose_diff` | Deliberately minimal. Give it browsing and it will "research" the constraint instead of recording it. |
| `scout` | `capture_page(url, breakpoints[], scale=2)`, `capture_section(selector)`, `extract_structure` (a11y tree + DOM → section inventory), `extract_tokens` (computed styles), `extract_brand` (logo/favicon/fonts), `crawl_links` | Two channels, and keep them separate: **computed styles give exact hex/px values; vision gives treatment and feel.** Never ask a vision model for a hex code when `getComputedStyle` exists. `capture_section` is product-critical — it produces the snippets shown at Gate 2 and throughout the content interview. |
| `design_director` | `read_blackboard`, `read_source_artifact`, `check_contrast` (deterministic WCAG), `render_specimen(palette, type_scale)`, `propose_diff` | No drawing tool — see below. |
| `content_editor` | `read_blackboard`, `read_source_artifact`, `ask_user_with_reference(question, snippet_image, draft)`, `web_search`, `fetch_url`, `propose_diff` | The `ask_user_with_reference` signature carries the source snippet *and* a generated draft, so the user reacts instead of composing. |
| `curator` | `ingest_asset`, `detect_pii` (OCR + NER), `redact_region`, `derive_variants` (deterministic), `remove_background`, `upscale`, `generate_image`, `edit_image`, `vision_diff`, `propose_diff` | Most of these are deterministic image ops (sharp/ImageMagick). Only `generate_image`, `edit_image`, and `vision_diff` need a model. |
| `builder` | `read_file`, `write_file`, `edit_file` (search-replace), `list_dir`, `grep`, `glob`, `run_command` (scoped allowlist), `read_blueprint`, `propose_diff` | Lovable and Orchids both mandate search-replace over full rewrites. `design_system` + `constraints` are **injected**, never fetched — fetching is skippable. The codebase lives on disk; the blackboard tracks section status and decisions, not file contents. |
| `inspector` | `screenshot(breakpoints[], scale=2)`, `get_a11y_tree`, `click`, `fill`, `scroll`, `read_console`, `read_network`, `run_axe`, `check_contrast`, `report_defects` | **No write tools.** Lovable ships both `read-console-logs` and `read-network-requests` and mandates debugging tools *before* reading code — worth copying. |
| `observer` | `read_blackboard`, `read_screenshots`, `compare_to_source`, `check_constraint`, `report_verdict` | **No write tools.** Rejections must cite a constraint or recorded decision by name. `check_constraint` is partly deterministic — "no blue" is a palette sample, not an opinion. |
| `orchestrator` | *(deterministic code)* | Applies/rejects diffs, validates schema, counts attempts, enforces the 3-cap. One model call it does own: turning failed criteria into two concrete user-facing options (CLAUDE.md §8). |

### On Figma

**Not for the design agent.** Figma Make is prompt → design → code inside Figma. Routing the
design step through it means outsourcing the core differentiator to a tool that has never seen
the brief, the constraints, or the sources — and it adds a lossy hop plus a second source of
truth between the design decision and the built page.

**Figma MCP is legitimately useful in the reverse direction**: a user who *arrives with* a Figma
file and wants it built. That is a v2 input source alongside reference URLs, handled by `scout`,
not a tool the design director reaches for.

### On mockups at Gate 2

A mockup that does not match the eventual build is worse than no mockup. Since the builder exists
and one section is cheap, **Gate 2 should show a real built hero**, plus the primary source
snippet and a palette specimen. Approvable, honest, and it exercises the build path early —
where failures are cheapest to find.

### Sizing

Orchids' main agent carries ~20 tools and works. But that is a generalist. A specialist with six
focused tools beats the same specialist with twenty; keep each agent under ~10 and let the
narrowness do the work.

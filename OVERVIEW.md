# Sparrow — an agent harness that builds business websites from a sentence

> One-page overview. For architecture rationale see `CLAUDE.md`; for the API see `backend/API.md`.
> Numbers below are measured from `logs/sparrow.jsonl` across ~20 real runs, not estimated.

## What it does

You type one line — *"a website for my agentic IDE"* — and paste two reference sites. Sparrow
turns that into a structured brief, studies the references with a real browser, proposes three
design directions as rendered swatches, asks you for your **actual** material (your logo, your
product screenshots, the facts it would otherwise have to invent), then builds a Next.js +
Tailwind site section by section, inspects what it built through the browser, fixes what is
off, and hands you a preview to approve.

Three things a human decides; everything else runs on its own:

1. **The brief** — what the site is for.
2. **The design direction** — one of three, shown as swatches, not prose.
3. **The material** — per image: your file, generate one, or leave it out. Per invented fact:
   confirm, correct, or keep the draft.

## Why it is different from Lovable / v0 / Emergent

Those take a prompt and guess at everything else. Sparrow refuses to guess at the two things
that decide whether the output is usable:

- **What the site is for.** Nothing is generated until a brief exists.
- **What real material it has.** Every AI-built business site dies on lorem ipsum and stock
  photos. Sparrow stops and asks — and shows you a snippet of the reference site so you know
  what it is asking for and why. Provenance is recorded per asset and per line of copy:
  *user-supplied* or *generated*.

Two smaller ideas that turned out to matter as much:

- **One primary reference, not a blend.** Blending six sites gives you the mean of six sites,
  which is generic by definition. Section order comes from the primary's own sequence.
- **Vocabulary open, budget closed.** The design agent may invent any treatment — grain,
  overlap, gradient, blur — but a separate pass decides which sections get which, and exactly
  one section carries the signature. This is what stops a page being either *flat* (every
  section the same) or *busy* (every section treated).

## How it is built

```
  Next.js console  ──SSE──▶  FastAPI  ──▶  orchestrator  ──▶  stages
   (frontend/)              (backend/)      (blackboard)        brief · sources · design
                                                │               compose · content · assets
                                                ▼               build · verify
                                     projects/<id>/            ──▶ Playwright (Chromium)
                                       blackboard.json         ──▶ LLMs (OpenAI / Anthropic / NVIDIA)
                                       asset-plan.json         ──▶ gpt-image-2, Veo 3.1 (ElevenLabs)
                                       workspace/  (a real Next.js project, built to static)
```

- **Blackboard, not agent mesh.** No agent talks to another. Each reads one shared, versioned
  document and proposes a diff; the orchestrator applies or rejects. Every transition is logged,
  so any run is replayable and any regression traceable to the diff that caused it.
- **Goal memory is a document, not a vector index.** The brief is small enough to inject whole
  into every prompt. Hard constraints ("no blue") are a verbatim list appended to every call —
  never summarised, never retrieved-maybe.
- **Build → look → fix.** After building, the harness screenshots its own output at desktop
  and mobile, runs a deterministic drift audit against the design system's recorded tokens,
  and asks a vision model about what the audit cannot measure. Loops are capped at 3.
- **Fixed stack.** Next 16, Tailwind 4, shadcn/ui, Motion. The model never spends reasoning
  on framework choice, and every pattern it emits is one it has seen ten thousand times.

**Note:** `CLAUDE.md` describes Postgres + Redis. The code does not use either — state is
`projects/<id>/*.json` on disk and the run is driven by one long-lived HTTP request. This is
fine for a single operator and is the first thing that changes for multi-tenant deployment.

## What a run costs and takes — measured

| | Typical | Range seen |
|---|---|---|
| LLM spend per site | **$8–13** | $3–13 |
| — of which inspector (vision) | $2.9–3.4 | the largest line item: ~40 calls × 12–16k input tokens |
| — builder | $1.1 | 7 sections |
| — design director | $1.0–1.2 | 4–5 calls, ~120k tokens of reference screenshots |
| — fixer | $1.1–1.3 | |
| Image generation | *not metered in $* | gpt-image-2, ~55s each, 4–6 per site |
| Video generation | *not metered in $* | Veo 3.1, one silent loop, ~2 min |
| Machine time | **35–45 min** | plus however long you sit at the two gates |

Reasonable all-in estimate with media: **$12–20 per site.** Total spend across every run
ever: **$94** in LLM calls.

Disk: ~300–770 MB per project, of which `workspace/node_modules` is ~560 MB. That is a real
Next.js install per site and is the second thing that changes for multi-tenant.

## What is proven vs. what is not

**Works end to end, repeatedly:** 17 projects have a built export. The video path has
completed 4 generations. The asset gate, content gate and design gate all round-trip.

**Measured gaps, none fixed** (from `CLAUDE.md §11`):

- **Verify does not reliably converge.** The inspector flags a generated image, the fixer's
  only available move is to delete it, a guard refuses, and the round burns. Observed again
  on the most recent run (`feature-detail: fix rejected — it removed …motion.mp4`).
- **Headings converge on the same sentence.** Seven sections drafted from the same brief
  with no knowledge of each other.
- **Generated imagery is unreadable up close.** Model choice, not architecture — but it is
  the thing that undercuts the real-content thesis.
- **The stage marker records the stage completed, not entered,** so a crash resumes one stage
  early and re-runs (and re-bills) a stage that already finished.
- **A crashed client kills the run.** The run lives inside the SSE response; close the tab and
  the generator dies mid-stage.

## What it would take to deploy

**As a demo you can send a link to (a weekend):**
one VPS (4 vCPU / 8 GB, ~$40/mo) with Chromium, Node, pnpm and Python; the FastAPI server
behind Caddy; the Next console as a static export or on the same box; API keys in env; a
`SPARROW_MAX_SPEND` per project. Everything runs as it does on your laptop.

**As something 1,000 people could sign up for (a month, minimum):**

| Must change | Why |
|---|---|
| Runs move off the request into a job queue (Redis + workers) | a closed tab currently kills the run |
| Blackboard moves to Postgres | concurrent writers, and `projects/` on one disk does not scale |
| A shared pnpm store, `node_modules` deleted after build | 560 MB × 1,000 users = 560 GB |
| Auth + per-user spend cap + a payment method | **$12–20 a site is the whole product decision** |
| Build workers isolated per run (container or Firecracker) | generated code runs `next build` on your box |
| Rate limits on every model call, retries with backoff | already partly there; needs to be everywhere |

The engineering is ordinary. The economics are not: at $12–20 a site, 1,000 users who each
build one site is **$12–20k in API cost**. Nobody gives that away.

## Is 1,000 users realistic?

Not as a free product. As a portfolio piece, *users* is the wrong metric anyway — a thousand
signups who each ran one free site and left proves less than fifty who paid.

Three shapes that could actually work:

1. **Bring-your-own-keys.** The user pastes their OpenAI / ElevenLabs keys; you charge nothing
   or a flat fee for the harness. Cost problem gone. Audience shrinks to people who have keys —
   which, for a *portfolio* project aimed at engineers and founders, is the right audience.
2. **Cheap mode.** Skip the vision inspector (the largest line), skip video, one image, one
   round. Probably $2–3 a site. Offer *one* free run per email and let people pay for the full
   pass. This is the realistic path to a thousand sign-ups.
3. **Pick a vertical and charge.** Local services — plumbers, clinics, restaurants — where a
   $49 site that uses their real photos is a plain win and there is nothing to explain.

## Why it is worth putting in a portfolio regardless

Not because of the demo. Because of what is in the repo:

- Every design decision is written down with the failure that motivated it, in the code, next
  to the code. *"This said 1280×720 whatever the file was"* is a sentence that only gets
  written by someone who measured.
- The architecture makes a real argument — blackboard over agent mesh, document over
  embeddings, closed budget over open vocabulary — and the argument is backed by observed
  failures, not preference.
- It is a full system: browser capture, vision inspection, a fix loop, human gates, image
  and video generation, provenance tracking, replayable logs, a console with live progress.
  Most "AI agent" portfolio projects are a prompt and a loop.

The honest pitch is not *"an AI that builds websites"* — that is a crowded room. It is
*"a harness that refuses to guess at the two things the others guess at, and records
exactly why every decision was made."* That is a thing an interviewer can ask you about for
an hour.

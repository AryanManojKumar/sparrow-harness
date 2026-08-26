# sparrow API

    sparrow serve --port 8000 --reload      # docs at /docs

Everything the frontend needs. A run takes minutes and stops twice for a human, so it is
not request/response: start it, stream progress, answer gates.

## The shape

    POST   /suggest                    autocomplete for the prompt box
    POST   /interview                  one sentence -> a structured brief
    POST   /projects                   create from a brief + reference urls
    GET    /projects                   list (unreadable ones are reported, not fatal)
    GET    /projects/{id}              blackboard, current stage, spend, recent log
    POST   /projects/{id}/advance      run until the next gate — SSE stream
    GET    /projects/{id}/gate         what is being asked, with options
    POST   /projects/{id}/gate         answer it
    POST   /projects/{id}/rebuild      re-make named sections or assets, then advance
    GET    /projects/{id}/directions   the design proposals at gate 2
    GET    /projects/{id}/assets       the per-image plan at the material gate
    POST   /projects/{id}/assets/{aid} upload the user's own image or logo (multipart)
    GET    /projects/{id}/preview/*    the built site, served statically
    GET    /projects/{id}/shots/{name} captures
    GET    /health

## Stages

    brief → [GATE 1] → sources → design → [GATE 2] → content → [MATERIAL GATE]
          → assets → build → verify → [GATE 3] → done

Four gates. Each is a decision only a human holds; everything between them runs without
asking. CLAUDE.md §8's rule is that gates are few, not that they are three — the count
that matters is "not fifteen", and an approval step that only ever hears yes is what §8
actually rejects.

The material gate (`gate:assets`, kept for compatibility) is the only one that is not a
choice between things the system produced. It is the point at which the user's **real
material** enters the run — both halves of it: their imagery, and the facts about their
business that the copy would otherwise have to invent.

`content` runs before it, drafting every slot on every section, so the handful of
questions the copy raises arrive in the same gate as the image questions rather than
opening a fifth stop.

## The front of the funnel

`POST /suggest` — completions for a half-typed prompt. An accelerator, never a step: it
returns empty on any failure rather than an error, so a slow or broken completion never
interrupts typing.

**It completes toward what is still unknown about the BUSINESS, not toward a website
shape.** A page shape chosen before the business is understood is a template, and §2 exists
so this system does not hand people templates. Four gaps, each with a bar, worked in order:

| gap | closed once | open | closed |
|---|---|---|---|
| `offering` | you know what it makes and to whom | "a bakery" | "a bakery supplying sourdough to restaurants" |
| `audience` | the buyer is named by role or situation | "restaurants" | "head chefs let down by inconsistent delivery" |
| `specifics` | one concrete checkable fact exists | "high quality" | "the same three loaves for nine years" |
| `purpose` | — only reachable once the first three clear | | |

A closed gap is left alone. Asking which three loaves deepens a gap instead of closing the
next one, and turns an interview into an interrogation.

```json
POST /suggest   { "q": "a website for my bakery", "limit": 3 }
-> { "gap": "offering",
     "hint": "Say what you make and who buys",
     "suggestions": [
       { "id": "business-customers", "category": "business customers",
         "text": "a website for my bakery that supplies bread and pastries to local cafés" } ] }
```

`gap` and `hint` are for the interface: show what the brief still needs, not only what
could be completed. Each row extends the user's own sentence by one clause, so accepting
one is progress rather than replacement.

`POST /interview` — the submitted prompt becomes a Brief, **without creating the project**.
The user sees what was inferred, corrects it, and only then commits. CLAUDE.md §2: nothing
is generated until the brief exists and is right.

```json
POST /interview  { "prompt": "a site for my SOC 2 compliance startup, we sell to fintech
                              engineers who've been through a painful audit. dont use blue,
                              our competitor is blue" }
-> {
  "brief": { "category": "B2B SaaS landing page", "tone": "…", "primary_action": "Book a demo" },
  "constraints": ["dont use blue"],
  "assumed": [
    "I assumed the product is software that helps teams manage SOC 2 compliance rather than
     a consulting-only service.",
    "I assumed booking a demo is the main conversion goal."
  ],
  "confidence": "low"
}
```

`assumed` is phrased so each line is correctable in one sentence — show them as editable
rows, not as a disclosure. `constraints` are the user's own words, extracted verbatim and
never paraphrased.

## Creating a project

```json
POST /projects
{
  "project_id": "acme",
  "product_name": "Acme Harness",
  "category": "Developer tool landing page",
  "offering": "An agent harness for codebases…",
  "audience": "Staff engineers at teams of 20-200…",
  "tone": "Precise and technical. No hype about velocity.",
  "primary_action": "Start free",
  "secondary_action": "Read the docs",
  "constraints": ["no purple - every dev tool is purple"],
  "urls": ["https://kiro.dev", "https://cursor.com"]
}
```

`product_name` comes from `/interview` and **must be passed through**. Pass an empty string
if the interviewer could not extract one; **GATE 1 then asks for it** and the run does not
reach a generating stage until it is answered. Do not send a placeholder — the gate is the
only place the name can be settled by the one party who knows it.

Measured across all eight real projects built before that gate existed: `product_name` was
`""` on every single one, and the consequences were visible on every page.

| where | what shipped without the name |
|---|---|
| nav brand mark | `<PhoneCall />` from lucide, `aria-label="Platform home"` |
| `<title>` | `"A platform for businesses to build voice AI agents q"` — the offering, cut mid-word |
| generated hero | a company called **Off-Hook**, invented by the image model and appearing nowhere else |
| generated showcase | **Off-Hook** again, but a different asset in the same run said **voiceowl** |

Two different companies on one page. The name now reaches four places, and each is tested:
the nav wordmark and the footer, the page title and description, `content_editor`'s copy,
and **the curator's asset briefs** — a generated dashboard is told what the product is
called so it renders the user's name instead of guessing one per call.

`tone` is the single strongest lever on how the site looks — see
`experiments/reactbits-01`, where changing that one line moved the design from austere to
kinetic. Worth surfacing prominently in the UI rather than burying it.

## Streaming a run

```js
const es = new EventSource(`/projects/${id}/advance`);
es.onmessage = (e) => {
  const { stage, kind, message, cost, spent } = JSON.parse(e.data);
  // kind: started | progress | blocked | awaiting | done | failed
};
es.addEventListener("end", () => es.close());
```

The stream ends when the run hits a gate, finishes, or fails. On `awaiting`, call
`GET /gate` for the question and options.

## Gate 2 shows pictures, not prose

The gate that fixes every visual decision downstream was asking things like *"a perforated
remittance-advice ribbon carrying real currency pairs"*. Nobody outside the design agent
can answer that. §8 requires concrete options a business owner can choose between.

Each direction is now **rendered**: its real palette as named swatches, its real typefaces
at real sizes, its buttons in its own colours, its signature in plain words. Alongside
them, a card showing **what the reference sites are actually painted with** — measured
from computed styles, not guessed from a screenshot.

    GET /projects/{id}/specimens/direction-0.png
    GET /projects/{id}/specimens/sources.png

The source card answers the real question behind light-versus-dark: *do you want what your
competitors have, or deliberately not.* Its subtitle counts it — "2 of 3 use a dark
ground" — so a user who wants the opposite can say so.

Every option carries a `specimen` URL. Show the images, not the text.

### "None of these"

The options include one with `choice: "other"`. Answer it with a `note` and the run goes
back to DESIGN and proposes three **new** directions against that instruction:

```json
POST /projects/{id}/gate  { "choice": "other", "note": "darker, not beige" }
```

The note is passed in as a correction to be taken literally, not a nuance to blend. A
`note` is required — without one there is nothing to steer by.

## Gate 2 is a choice, not an approval

The design agent is **deterministic** — three runs on identical inputs produce
byte-identical output (`experiments/variance-01`). So re-rolling a rejected direction
returns the same one, and an approve/reject gate would be inert.

Instead the stage proposes **three directions up front**, each ruling out the last:

```json
GET /projects/{id}/directions
[{ "index": 0, "signature": "The Review Gutter — …",
   "atmosphere": "…", "type": "Recursive / Public Sans",
   "revised": "what the uniqueness pass discarded" }, …]
```

Answer with the index:

```json
POST /projects/{id}/gate   { "choice": 0 }
```

"Which of these" is answerable by a business owner. "Is this good" is not.

## The asset gate

Every AI-built business site dies on stock imagery. CLAUDE.md §2 makes real material the
differentiator, and until this gate existed there was no moment in a run at which a user
could hand the system a file: `curator` read each blueprint's asset briefs and generated
all of them. `Provenance` carried `user_supplied | restyled | generated` from the start
and recorded `generated` every time — which is what a missing gate looks like in the data.

The run stops after the design direction is chosen (so the restyle has a design system to
restyle *to*) and before `assets` runs.

### What the gate asks

```json
GET /projects/{id}/gate
{ "awaiting": true, "gate": "gate:assets",
  "question": "9 image(s) go on this page. For each one: use your own file, have one
               generated from the description, or leave it out?",
  "options": [
    { "asset_id": "product-showcase-1",
      "section_id": "product-showcase",
      "brief": "One product capture showing the unified payments control surface…",
      "prominence": "supporting",
      "uploaded": false,
      "choices": [
        { "choice": "upload",   "label": "Use my own image",
          "detail": "Restyled to the chosen design direction. Any text it gains that the
                     original did not have is rejected.",
          "post_file_to": "/projects/{id}/assets/product-showcase-1" },
        { "choice": "generate", "label": "Generate one from this description" },
        { "choice": "skip",     "label": "No image — build the section from type and layout" }
      ] } ] }
```

`brief` is the blueprint's own words — show it, because it is what a generated image
would be made from and what an uploaded one is expected to show. `prominence` is
`dominant | supporting | thumbnail` and says how large the image lands: a user deciding
whether to go and find a real screenshot needs to know whether it will be the biggest
thing on the page or a 200px tile.

The same list is readable on its own at `GET /projects/{id}/assets`, before the gate and
after it, so the interface never keeps its own copy.

### The other half: invented facts

The copy is drafted by `content_editor` before this gate, and it reports every line where
it had to assert something about the business that the brief does not support — a count, a
price, a customer name, a quotation. Those arrive as options with `"kind": "fact"`:

```json
{ "kind": "fact",
  "ask_id": "testimonial-1",
  "section_id": "testimonial",
  "slot": "quote",
  "question": "Can you provide an approved quote from an engineer who uses the IDE?",
  "draft": "It helps me follow the code before I touch it…",
  "invented": "the engineer quotation",
  "source_example": "",
  "choices": [
    { "choice": "answer", "label": "Give the real answer",
      "detail": "Used verbatim, and never redrafted afterwards.", "field": "text" },
    { "choice": "keep",   "label": "Keep the draft as written" } ] }
```

Image options carry `"kind": "image"` and are otherwise unchanged, so one pass over
`options` splits into two lists under one heading.

**Expect few of these, and sometimes none.** The ide blueprints produce 0 asks for a nav,
0 for a hero and 1 for a testimonial. A section with 39 slots does not produce 39
questions — §11 is right that nobody fills in a 39-field form, so the agent drafts
everything and asks only where it invented a checkable fact. The count varies run to run:
it is a model judgement, not a deterministic check.

Show `draft` as the pre-filled value so the user edits a line rather than facing a blank
box, and `invented` so they can see what they are being asked to confirm.

### Answering

**Per asset, not once for the run.** This is the whole point of the gate: a founder has a
real dashboard screenshot for the hero and nothing at all for the integrations strip. One
global choice forces them to fabricate the second or lose the first.

```json
POST /projects/{id}/gate
{ "assets":  { "product-showcase-1": "upload",
               "feature-grid-1": "generate",
               "logo-wall-1": "skip", "testimonial-1": "skip" },
  "content": { "testimonial-1": "Used by 12 teams at Acme.",
               "hero-1": "" } }
-> { "stage": "assets", "decisions": { … }, "content_answered": 1 }
```

`choice` is ignored at this gate. Every asset in the plan must appear in `assets`; a
partial answer is a `400` naming the ones still undecided. There is deliberately no "do
the same for all of them".

`content` is optional and keyed by `ask_id`. An empty string or an omitted id keeps the
draft — both close the ask, so the gate never asks twice. An answer that is actually typed
replaces the slot and marks it `user_supplied`, which means nothing downstream will
rewrite it. An unknown `ask_id` is a `400` rather than a silent no-op: the user typed a
real fact about their business and must not be left believing it was recorded.

Content answers are applied **before** asset decisions, so a bad asset payload cannot
discard the facts the user just typed.

### Uploading

```
POST /projects/{id}/assets/{asset_id}
Content-Type: multipart/form-data     file=@dashboard.png
-> { "asset_id": "product-showcase-1", "stored": "product-showcase-1.png",
     "bytes": 1232923,
     "next": "answer the asset gate with this asset set to 'upload'" }
```

PNG, JPEG or WebP, up to 25MB. **Post the file first, then answer the gate.** Answering
`"upload"` for an asset with no file is a `400`, not a quiet fall back to `generate` — a
silent fallback is exactly how every site in this category ends up full of pictures nobody
chose. An upload posted before the gate is answered survives the gate being re-asked, so a
crash between the two does not lose the file.

### What each choice does

| choice | what runs | recorded provenance |
|---|---|---|
| `upload` | the file is **scrubbed of personal and customer data**, then restyled to the chosen design system, and the restyle is checked for text fidelity | `restyled`, or `user_supplied` if the check rejects it |
| `generate` | `curator.generate` from the blueprint's brief — the previous behaviour | `generated` |
| `skip` | nothing; no asset is recorded and the builder composes the section from type and layout | — |

### The PII scrub on uploads

An uploaded dashboard is full of real customer data. The capture this was built against
carries a named user, their work email, a merchant id, five card and transaction ids and
eleven sterling amounts — and before the scrub existed the fidelity gate faithfully
preserved every one of them into the published page.

**It is not a gate.** There are three gates and a fourth would not get finished; more to
the point, there is no version of "yes, publish my customer's email address" worth
stopping the run to ask. It runs automatically and **reports what it changed** on the
event stream:

```
{ "stage": "assets", "kind": "progress",
  "message": "product-showcase-1: real values substituted out of your screenshot before
              anything else saw it — email ×1, identifier ×10, money ×11, org name ×3,
              person name ×1" }
```

The same summary is on the asset as `Asset.scrubbed`. It carries the CATEGORY and the
count and never the value it replaced: that field is read by agents, written into prompts
and copied into logs, which are the paths the scrub exists to keep the value off. The
scrubbed image is written beside the upload as `uploads/{asset_id}--scrubbed.png`, so the
substitution is the user's to check.

Values are **substituted, not blurred** — same length, same currency symbol, same digit
count, same ink, same position. A dashboard screenshot is only worth uploading because it
looks like real software in real use; a scrub that greys out every figure returns
something worse than the leak, because the user stops uploading. Product UI chrome, menu
items, column headers, status words, timestamps, counts, code and repository names are
left alone, and a value that cannot be placed confidently is masked rather than left
readable.

The scrub runs **before the restyle**, not after. `restyle` posts the file to a
third-party image model and what comes back is published at the preview URL; after either,
the data has already left.

A replacement is only ever painted on the row the model pointed at. Nothing overrides
that bound — where the value is not on that row, the scrub masks there instead of hunting
for it elsewhere. There used to be a rescue pass that widened the search past the
neighbouring rows, and it is how a beneficiary's name came to be painted across the
`View all activity ›` link at the foot of a table. Measured over five locate responses
for one capture, **5.1% of placements landed on another row; after the bound, 0 of 112**.
Matching cannot do this job: in-row match errors ran 0.115–0.599 and crossing errors
0.450–0.579, one distribution on top of the other. The cost is masking a little more —
9 masks became 15 over those same responses — which is the right way round.

It reads its own output back and retries once, **masking** whatever still reads rather
than substituting it a second time — the second pass places against the same approximate
box and makes the same mistake, and one masked name beats a published one. Where too much
still reads even so, it **stops substituting and masks every located value instead**, and
the event says so.

Density is what decides how much of a capture survives as substitution rather than mask.
On a dense trade-finance capture — 36 findings, several near-identical account numbers
stacked in one narrow column — the row bound holds (no placement lands on the wrong row)
but a third of the findings cannot be placed on their own row at all, so 24 are
substituted and 12 masked, against 21–23 and 3–5 on the payments dashboard. The masked
version is uglier and it is honest, and the answer is a simpler capture. **A capture that
dense is the known limit of this approach** — not because it comes out wrong any more, but
because it comes out grey.

The read-back is what makes any of this checkable, and it looks for two things: values the
locate pass named that are still legible, matched on shared words rather than exact string
because the two reads of a row disagree (`Foo Food Suppliers Ltd` one pass,
`To Food Suppliers Ltd` the next — on an exact test that row shipped unscrubbed while the
report said otherwise); and money- and email-shaped strings the locate pass **never named
at all**, which nothing was checking before. Both get masked.

**This is a distribution, not a fixed result.** The model returns different boxes and
finds slightly different values on every run, so the honest way to describe the scrub is a
rate over repeated runs, never a single sample. Over five live runs of the same upload:
21–23 values substituted, 3–5 masked, 0 placements on the wrong row, 0 of 24 real values
surviving. Expect the substituted/masked split to move run to run; expect the last two
numbers not to.

### The fidelity gate on uploads

Only the upload path is gated, and the asymmetry is deliberate. A generated image invents
its contents by construction — that is the point, and gating its text would gate the
mechanism. A restyled image is still a picture of the user's **real product**, so any word
the model adds is a claim they never made.

Measured in `experiments/image-probe-02`: asked to clean a capture whose copy was truncated
by a chat widget, the model completed the sentences — "frameworks, adapt", "visibility
across", "grow with you" — plausibly, well, and entirely invented. The output looked
flawless.

So both images are transcribed and compared at word level (a restyle legitimately reflows
text, so line breaks move; a word that was not there before is the defect). A restyle that
invented words is **discarded in favour of the user's own screenshot**, the asset is
recorded as `user_supplied`, and the reason lands in `Asset.rejected` and in a `blocked`
event on the stream. Their real screenshot, unstyled, beats a beautiful one that says
something untrue about their product.

The comparison is **scrubbed-against-restyled**, never upload-against-restyled. The gate
asks whether the image model invented copy, so the ground truth is what the image model
was given. Measured against the upload instead, every substitution the scrub made reads as
a word the restyle invented and every legitimate restyle of a dashboard is rejected. What
falls back on a rejection is the scrubbed image, not the upload — the restyle failing is
no reason to publish the customer data.

There is one restyle attempt and no retry: the failure mode is the model inventing copy,
and a second roll of the same prompt is not evidence it will invent less.

### Nothing to decide

If no blueprint asks for imagery, the gate does not stop the run. A project created before
this gate existed has no plan on disk and generates everything, exactly as it did before.

## Notes for the frontend

- **SSE, not websockets** — one-way progress is all a run needs.
- **Costs are live.** Every event carries its own `cost` and the running `spent`. A full
  run is roughly $1.10; worth showing, since users are spending real money per click.
- **Preview is the real static export**, so it can go straight in an iframe. Its HTML is
  built for a site root, so root-absolute `/_next/…` and `/assets/…` references are
  rewritten to the `/projects/{id}/preview` prefix on the way out. Without that the page
  renders as unstyled text with no images, which looks like a failed build rather than
  wrong paths. The `out/` directory itself stays portable — nothing is baked in at build
  time.
- **Old projects may be unreadable.** The schema moved during development; `GET /projects`
  flags those rather than failing.
- **`_RUNS` is in-process.** Restarting the server loses stage position, though nothing on
  the blackboard. Fine for one machine; needs Redis before more than one.
- **Disconnecting does not stop the run.** Deliberate: closing a tab should not throw away
  eight minutes of extraction already paid for. Reconnect with `GET /projects/{id}` for
  the current stage, `advancing`, and the log so far.
- **A second `/advance` while one is in flight returns 409.** Two generators over the same
  stages write the same files and bill twice, so it is refused rather than queued.
- **The asset gate answer has a different shape from the others.** Gate 2 takes a
  `choice`; the asset gate takes an `assets` map and rejects a bare `choice`. Worth a
  distinct component rather than reusing the gate widget.
- **A source that will not load is skipped, not fatal.** `extract()` has a 90-second
  wall-clock budget per site; stripe.com intermittently hangs under bot protection rather
  than erroring, and a hung source used to block the whole run silently. The run continues
  with whatever sources did load, and needs at least two.

## Logging and tracing

Everything is written as **JSONL** — one self-describing event per line, appended to a
global `logs/sparrow.jsonl` and a per-project `projects/{id}/logs/run.jsonl`. Per-project
first, because the question is always "what happened on *that* run", and grepping one file
beats filtering a global one.

Four kinds: `http`, `stage`, `llm`, `error`. Correlated by `trace_id` (one per run) and
`span_id` (one per model call), carried in a contextvar so an agent deep in the stack does
not have to be handed them.

    GET /projects/{id}/logs?kind=llm&limit=200     replay
    GET /projects/{id}/logs/summary                what it cost, by agent

### Model calls

The expensive, non-deterministic part, and the part you cannot reconstruct afterwards.
Logged at the provider — the single choke point every call passes through, including ones
curator and the ranking helpers make without going through an Agent:

```json
{"ts": 1787574058.4, "kind": "llm", "message": "interviewer → gpt-5.6-luna",
 "trace_id": "2b2d33bacaae43ad", "project": "acme", "stage": "design",
 "span_id": "5bfad642", "duration_ms": 2674, "cost": 0.0000086,
 "data": {"agent": "interviewer", "provider": "openai", "tier": "cheap",
          "tokens": {"input": 19, "cached": 0, "output": 4, "cache_hit": 0.0},
          "prompt_sha": "32dd1a16b25e", "images": 0}}
```

`prompt_sha` is a hash of the exact system+user text, so two runs that diverged can be
diffed down to the call where they stopped matching — without storing every prompt.

Prompt and response text is stored, capped, only behind `SPARROW_LOG_PROMPTS=1`
(`SPARROW_LOG_PROMPT_CAP`, default 4000 chars). It is bulky and sometimes carries a
client's real material, so it is opt-in.

### Summary

```json
GET /projects/acme/logs/summary
{ "llm_calls": 34, "total_cost": 1.1043, "wall_seconds": 712.4,
  "by_agent": { "builder": {"calls": 6, "cost": 0.8718, "in": 17862, "out": 27532},
                "design_director": {"calls": 3, "cost": 0.3413, …} } }
```

`by_agent` is sorted by spend. On a typical run the builder is ~80% of it.

### Console

The same events print readably to stderr:

    llm   builder          gpt-5.6-sol         3,002 in (90% cached)  5,593 out  $0.1828  47210ms
    http  POST   /projects/acme/advance        200 5393ms

`SPARROW_LOG_LEVEL=WARNING` quietens it without affecting what is written to disk.

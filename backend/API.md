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
    GET    /projects/{id}/directions   the design proposals at gate 2
    GET    /projects/{id}/preview/*    the built site, served statically
    GET    /projects/{id}/shots/{name} captures
    GET    /health

## Stages

    brief → [GATE 1] → sources → design → [GATE 2] → assets → build → verify → [GATE 3] → done

Three gates, per CLAUDE.md §8. Everything between them runs without asking.

## The front of the funnel

`POST /suggest` — completions for a half-typed prompt. An accelerator, never a step: it
returns `{"suggestions": []}` on any failure rather than an error, so a slow or broken
completion never interrupts typing.

```json
POST /suggest   { "q": "a website for my compliance", "limit": 5 }
-> { "suggestions": [
     { "id": "compliance-software",
       "text": "a website for my compliance management software — product features, audit …",
       "category": "Compliance Software" } ] }
```

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

## Notes for the frontend

- **SSE, not websockets** — one-way progress is all a run needs.
- **Costs are live.** Every event carries its own `cost` and the running `spent`. A full
  run is roughly $1.10; worth showing, since users are spending real money per click.
- **Preview is the real static export**, so it can go straight in an iframe.
- **Old projects may be unreadable.** The schema moved during development; `GET /projects`
  flags those rather than failing.
- **`_RUNS` is in-process.** Restarting the server loses stage position, though nothing on
  the blackboard. Fine for one machine; needs Redis before more than one.

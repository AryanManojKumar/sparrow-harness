# image-probe-01 — can a model generate product UI worth shipping?

CLAUDE.md §7 assumes frontier image models "now handle precise UI regeneration well
enough". That assumption decides what `curator` is: an image generator, or a treatment
engine for user-supplied screenshots. It had never been tested here.

One brief — the real one `blueprinter` wrote for the ide-01 hero — given to three models.

## Result

| model | verdict | notes |
|---|---|---|
| **gpt-image-2** | **usable** | Dense, convincing product UI. Agent-run list with statuses and durations, unified diff with syntax colouring, a review checkpoint. Plausible TypeScript: `async findByEmail(email: string): Promise<User \| null>` |
| gpt-image-1.5 | usable | Clean and fully legible, slightly more generic. Valid Python, sensible controls |
| google/nano-banana (via Kie) | **not usable** | Text garbled throughout — "hablisf", "hablibf", "Peafix", "Implemant", "Compled Runs". Reads as an illustration of a UI, not a UI |

Timing: 39s, 44s, 85s respectively.

**§7's assumption holds — but only for OpenAI's image models.** Nano Banana's reputation
for text rendering does not survive contact with dense monospace at small sizes.

## The defects that justify the vision diff

Even the winner is wrong in ways a careless pipeline would ship:

- `privete repo: UserRepository` — a typo in code that reads as real
- line numbers run `42, 43, 44, 45, 46, 43, 48, 43, 43, 58` — jumbled
- duplicate line numbers in the second hunk

At a landing page's display width these vanish. Zoomed, or in a hero that bleeds large,
they do not. §7's vision-diff safeguard is not optional, and this is the evidence.

## What this decides about curator

Generation is viable, so `curator` generates rather than only treating. Its shape:

1. **generate** product captures from the blueprint's asset briefs — `gpt-image-2`
2. **vision-diff** every output against its brief — garbled text, invented controls,
   nonsense numbers. This is a gate, not a report
3. **treat** the accepted image per `design_system.imagery_treatment` — frame, bleed,
   shadow. §7: presentation carries most of the visual quality independent of the asset
4. **derive variants** — deterministic, sharp
5. PII scrub deferred until real uploads exist

## On Veo

Veo is video. All nine asset briefs say "product capture showing X", so it is the wrong
tool for them — a generated five-second video of a fake UI has the same garbled-text
problem as a generated image, moving.

Where it may earn its place: the register measured **3/4 dev-tool sources using video**,
and §7 lists backdrops and texture as in scope. Ambient background loops are a real use.
That is a later question, and a separate one from product imagery.

Kie's endpoints are recorded for when it is: `POST /api/v1/veo/generate`, poll
`/api/v1/jobs/recordInfo?taskId=`, and the result CDN rejects a default user-agent.

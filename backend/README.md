# sparrow — backend

The harness. FastAPI arrives when there is a UI to serve; right now this is the
core loop as importable modules plus a thin CLI, because an HTTP layer over a
loop that does not work yet is the wrong order.

## Setup

    uv sync
    cp .env.example .env      # add your ANTHROPIC_API_KEY
    .venv/bin/playwright install chromium

## Layout

| Module | Does |
|---|---|
| `blackboard/schema.py` | Pydantic models. **The single source of truth** |
| `blackboard/store.py` | Versioned store. One write path — RFC 6902 patches in, `Applied` or `Rejected(reason)` out |
| `render/tokens.py` | `DesignSystem` → CSS **and** → prompt fragment. Both derived, neither authored |
| `agents/base.py` | Prompt assembly. Brief/constraints/design-system injected into every call |
| `agents/builder.py` | The builder. One section per call, blind to the others |
| `audit.py` | Deterministic drift audit, driven by the same `DesignSystem` the builder saw |
| `capture.py` | Playwright. **Scrolls before it shoots** |
| `fixtures/ledgerline.py` | The design system from `experiments/drift-test-01`, as the audit's regression baseline |

## Three invariants

**One write path.** Nothing mutates the blackboard except `Store.apply`. Rejections
carry a reason the proposing agent can read and act on, not an exception.

**Injected, never fetched.** There is deliberately no `get_brief` tool. A fetch is
skippable; an injection is not.

**Derived, never duplicated.** The token CSS and the prompt fragment are two
renderings of one object. Two hand-maintained copies of the same decision is the
bug this design exists to prevent — Lovable documents exactly that failure in its
own prompt, one layer down.

## Closed enumerations

`Scale.closure()` generates the sentence — *"9 values. There is no 10th."* — from
the data, so it can never disagree with the values it describes.
`experiments/drift-test-01` measured why this matters: closed sets held perfectly
across five independent builds, open scales leaked.

## CLI

    sparrow new <project>          # workspace from the scaffold + install
    sparrow tokens <blackboard>    # render design_system into globals.css
    sparrow prompt <blackboard>    # print the injected design-system fragment
    sparrow audit  <blackboard>    # deterministic drift audit; exit 1 on findings
    sparrow shoot  <out-dir>       # scroll-then-capture at three breakpoints

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Sparrow console — frontend rules

> **These rules OVERRIDE default behaviour, for every AI and every person.** Claude reads
> them through `CLAUDE.md` (which imports this file); Codex, Cursor, Copilot and Gemini read
> `AGENTS.md` directly. When a rule here conflicts with a habit, the rule wins. The root
> `CLAUDE.md` (architecture, why the harness is shaped this way) also applies.
>
> The block above this heading is Next.js's own and is rewritten by `next dev`. Edit only
> below it.

**Rules are held by tools, not by reading.** This repo's own finding (root `CLAUDE.md` §6):
a number in a prompt does not move anyone; an audit that fails does. So:

- `pnpm check:changed` (types, plus lint, format and related tests on the changed files)
  runs on **every commit that touches `frontend/`** through the git pre-commit hook in
  `.githooks/`, enabled by `pnpm install`.
  **Never bypass it with `--no-verify`.** If it fails, the change is not done.
- `pnpm perf` (Lighthouse ≥ 98 + JS budget) runs when committing a change to UI or
  dependencies. It needs the backend, so it is not in the hook.
- Every lint rule marked *(lint)* below is an ESLint error in `eslint.config.mjs`.
  A rule that cannot be linted is in the PR gate at the bottom.

### When the checks run — at commit time, only for what changed

Checks cost minutes and real money in tokens, so they run **only when asked to commit**,
and **only for the files that changed**:

- **While making a change: run nothing** — no `pnpm check`, `pnpm perf`, `next build`,
  lint, format or tests, and never after each edit. Write the code to these rules.
- **Backend-only commit** (no file under `frontend/` changed): **no frontend check at all.**
- **Frontend commit:** `pnpm check:changed` — typecheck, then lint, format and the related
  tests **on the changed files only**. The pre-commit hook runs the same thing on the staged
  files. The full-project `pnpm check` is only for when asked for it explicitly.
- **`pnpm perf` only when `check:changed` says it is due** — UI, styles, dependencies or
  what a page loads changed (`src/**/*.tsx|css`, `src/app/`, `package.json`, the lockfile,
  `next.config`). Docs, tests, scripts or `src/lib` logic alone do not need it.
- Paste the output; fix anything that fails; then commit.

Exceptions: the user asks for a check by name, or a check's output is needed to diagnose a
reported bug.

## Boundary

The console **renders state and dispatches intent**. The office API (`backend/`, :8000)
owns every stage, gate, decision, spend figure and piece of provenance; the console shows
what the API returned and never infers it. It never talks to a model provider, the
workshop or the gateway, and never holds a key. The only environment value it reads is
`NEXT_PUBLIC_API_URL` — and everything `NEXT_PUBLIC_*` is public.

## Stack & commands

Next 16 App Router · React 19 · TypeScript `strict` · Tailwind 4 with theme tokens in
`src/app/globals.css` · shadcn primitives on `radix-ui` · `lucide-react` icons ·
`next/font` (Geist). Vitest for unit tests. **No new UI kit, CSS framework, state library
or animation library without a written reason in the commit.** Before using a Next API,
read its page in `node_modules/next/dist/docs/` (the block above says why).

```bash
pnpm dev            # :3000, talks to the office API on :8000
pnpm check:changed  # the commit gate: changed files only (what the hook runs)
pnpm check          # the same, whole project — only when asked for
pnpm perf           # production build, JS budget, Lighthouse medians — the merge gate
pnpm check:all      # both
pnpm format         # prettier --write
```

## Structure & layering

```
src/app/            routes only — thin page.tsx / layout.tsx that compose components
src/components/     feature components (flat today — see Known gaps for the target tree)
src/components/ui/  shadcn primitives: presentational, no data, no API calls
src/lib/            transport (api.ts, suggest.ts), pure helpers (urls, utils), types
```

- **Components render and dispatch; `src/lib` owns transport.** No `fetch` in `src/app` or
  `src/components` *(lint)*; `src/lib` never imports a component *(lint)*.
- **One container per screen owns data** (`build-workspace.tsx` for `/build`,
  `prompt-console.tsx` for `/`); children take props and call back.
- A component used in two places moves to `components/ui` (primitive) or stays shared in
  `components/` — never copied. New components stay under ~250 lines; a file that grows
  past it is split in the same change.
- Import with the `@/` alias, never `../../`.

## Modern React & Next only

| Don't | Do |
|---|---|
| `"use client"` on a whole page | Server component by default; client only where state or handlers live |
| `useEffect` to copy or derive state | compute during render, or `useMemo` |
| `setState` directly in an effect body | event handlers, `useSyncExternalStore` for outside values *(lint: `react-hooks/set-state-in-effect`)* |
| writing `ref.current` during render | in an effect or handler *(lint: `react-hooks/refs`)* |
| `forwardRef` | `ref` as a prop (React 19) |
| urgent `setState` for data that arrived in the background | `startTransition` (`inTransition()` in build-workspace) |
| importing a heavy panel directly | `@/components/lazy-panels` *(lint)* |
| `motion` / JS animation | CSS transitions/keyframes on `opacity`/`transform` *(lint: import blocked)* |
| `<script>` in JSX | never — React does not run it on the client *(lint)* |
| `any`, `as unknown as` | `unknown` + narrowing *(lint: `no-explicit-any`)* |
| `console.log` | nothing shipped logs *(lint)* |
| `catch {}` | handle it, or one comment line saying why ignoring is safe *(lint: `no-empty`)* |
| `<img>` for page assets | `next/image`; plain `<img>` only for API-served images, with an inline reason |

## Requests & async

- **Billable calls** — `/interview`, `/suggest`, `/projects/{id}/advance`, `/gate` answers,
  `/studio/turns`, rebuilds — cost real money. They are **never called automatically or
  as a side effect of opening a screen, never retried, and guarded against double fire**
  (an in-flight flag checked in the handler; `disabled` alone does not stop Enter or a fast
  double click). Show the running spend where they are triggered.
- **Only idempotent reads may retry**, with bounded backoff.
- User-driven requests are **cancellable**: an `AbortController` per request, aborted on
  unmount and when a newer request supersedes it (typing in the prompt box).
- A run is **one** server-sent-events stream (`advance` or `follow`), closed on unmount.
  Opening a project follows a run already in flight; it never starts one.
- Background data (plans, asset lists, pages, ideas) is applied in a transition.

## Forms & validation

Every rule the API enforces is **mirrored on the control, shown next to it, and blocks
submit with a visible reason** — never only in a toast, never below the fold. The API
stays the authority. Rules to mirror today: two full `https://` reference URLs; every
asset slot answered; a logo is `upload` or `wordmark`, never skipped; uploads are PNG,
JPEG or WebP up to 25 MB; a typed fact replaces the draft verbatim.

## Loading, empty, error

Every API call shows it is happening — an idle-looking screen gets clicked twice.
Reads: a skeleton **the size of what replaces it** (see Performance). Writes: progress on
the control that started it, labelled in the present participle ("Starting…",
"Stopping…"). Loading, empty and error are three explicit states, and a failed request
returns the UI to an interactive state with a way to retry.

## Errors

The API returns FastAPI's `{ "detail": … }`. It is turned into user-facing text in
`src/lib`, in one place; never show a raw status, `answer gate failed (400)`, or a stack.
A gate refusal (400) keeps the gate open with the reason on it.

## The preview iframe (the hard part)

The built site is served same-origin through the rewrite in `next.config.ts`, so the
address bar can follow it and **Select** can inspect it. Rules:

- It is a **facade until user intent** (`useUserPresent` in `preview-pane.tsx`): booting
  the generated site on load cost 790 ms of blocked time and brought its own layout
  shift into ours.
- Links into it come only from paths the API returned, under the project's preview base.
- **Security, not yet solved:** same-origin means the generated site's JavaScript — which
  a model wrote — runs with the console's privileges and could read `sessionStorage` or
  call the API. Do not widen this (no tokens or secrets reachable from the page). The fix
  is a separate preview origin and a `postMessage` inspector — the office/workshop split
  applied to the browser.

## AI output is untrusted text

Studio replies, idea cards, the interviewer's brief, drafted copy, anything a model wrote:
render as text (`whitespace-pre-line`). **Never `dangerouslySetInnerHTML`** *(lint)*,
`eval` or `new Function` *(lint)*. Markdown, if ever, goes through one sanitising
component chosen deliberately.

## Auth

Not built — deferred until the product is finished (decision recorded 2026-11-16). When
it lands: access token in memory only, never in `localStorage`, `sessionStorage`, a URL or
a log; refresh in one interceptor-style place in `src/lib`; screens never do their own 401
handling.

## Security

No secrets in the bundle. No external scripts or stylesheets — fonts through `next/font`.
External links get `rel="noopener noreferrer"`. The user's prompt, brief and reference
URLs never go into a URL or query string (they travel via `sessionStorage`); routes carry
only the project id. Hiding a button is not authorisation — the API decides.

## Styling

Theme tokens only: colours are `--background`, `--primary`, `--muted`… from
`globals.css`, used as `bg-primary`, `text-muted-foreground`. **No raw hex and no raw
palette classes (`emerald-400`, `amber-…`) in new code** — add a semantic token instead.
The console is **dark only**, by design (an operator screen, not a generated site).
Respect `prefers-reduced-motion` on every animation.

## Performance — Lighthouse ≥ 98, layout shift 0

Held by `pnpm perf`: median of 5 mobile / 3 desktop runs ≥ 98 on `/` and `/build` (one
temporary exception: `/build` mobile is gated at **97** — see Known gaps), no run with layout
shift, and first-load JS within budget (home 200 KB, `/build` 205 KB gzip;
191 / 195 measured 2026-11-18 — Next + React are ~150 KB of that). Raise a budget only with
a measured reason in the same commit. Measure production builds only — `next dev` scores
mean nothing. `PERF_PROJECT=<id>` picks the project `/build` is measured on.

Traps that already cost points — each fix is in place and commented where it lives:

| Trap | Cost | Rule |
|---|---|---|
| Chat column changed sides once the project loaded | CLS 0.69 → score 77 | Layout boxes never move after first paint; `WorkspaceFrame` is shared by the shell and the live workspace |
| Built site booting in the preview on load | 790 ms blocked + its own CLS | The iframe is a facade until intent |
| Two branches rendering a `<div>` in one slot | CLS 0.038 | Key sibling branches so React replaces, not morphs |
| Content arriving late above other content | CLS 0.01–0.04 | Late content goes below everything, or its slot exists at a fixed size from first paint |
| `motion` for one fade | home mobile LCP | No animation library on first load |
| Live SVG `feTurbulence` on phones | 10 s blocked, home mobile 56 | No live filters under 768px |
| Big post-fetch updates as urgent state | 84–240 ms blocks | Transitions; the workspace's first commit is the shell |
| All panels in the first download | one unsliceable commit | `lazy-panels.tsx`, each placeholder filling its box |
| Font variable pointing at itself | everything in Times New Roman | Fonts only via `next/font`; preload only the headline face |
| Inline `<script>` rendered by a component | console error on every navigation | Never |

Lighthouse is a lab test on one simulated phone: ≥ 98 means *in that test*. It stops us
making the console slower; it does not promise every device.

## Accessibility

Icon-only buttons need `aria-label`. Use real `<button>`/`<a>`, never a clickable `<div>`.
Everything is keyboard-operable with a visible focus style. Run progress and gate changes
are announced with `aria-live`. Modals trap and restore focus.

## Formatting values

One helper each, in `src/lib`: money (spend), stage labels, page names (`pageName`).
Never format the same value two ways on one screen.

## TypeScript, naming, comments

`strict`; no `any` *(lint)*; no `!` on values that can really be null; `import type` for
types. Files kebab-case (`build-feed.tsx`), components PascalCase, hooks `useX`, API
functions verb-first (`getGate`, `answerGate`) — never `handle`/`process`/`data`.
**Comment the why, never the what** — and when a rule here exists because something
broke, the comment names the measured cost.

## Testing

Vitest, files beside the code as `*.test.ts`, names `subject_scenario_expected`. Test what
users rely on: request/error mapping, the event-stream parser, stage status derivation,
gate-answer building, the preview facade. Every new `src/lib` function ships with a test.
Component tests (jsdom + Testing Library) are added with the first one that needs them.
Never delete a test without approval.

## Known gaps — where the code does not yet meet these rules

Listed so that nobody "fixes" one unasked, and nobody reads the code and concludes a rule
is not real. Close them deliberately, one per change. Counts measured 2026-11-18.

| Gap | Where |
|---|---|
| Flat `src/components/`; target is `features/home`, `features/workspace/{gates,studio,preview}`, `shared/ui`, `lib/api/*` | whole tree |
| 7 files over 300 lines | studio-panel 1009, build-workspace 640, preview-pane 550, gate-panel 542, prompt-console 385, build-feed 341, lib/api.ts 566 |
| 5 `eslint-disable … known debt` for `set-state-in-effect` / `refs` | `grep -rn "known debt" src` |
| Requests not cancellable (`AbortController` in 2 places) | lib/api.ts, lib/suggest.ts |
| No single error mapper — error text built per call | lib/api.ts |
| URL rule shown below the reference box, not beside Send | prompt-console.tsx |
| 63 raw palette classes, 8 raw hex values | mostly status colours; preview window chrome |
| Spend formatted as `toFixed(2)` and `toFixed(4)`; stage labels in two maps | workspace-tabs, build-feed, build-workspace |
| Reference-site favicons fetched from `google.com/s2/favicons` (an external request that tells Google the reference domains) | favicon.tsx |
| Generated preview runs same-origin | see The preview iframe |
| Chat divider is pointer-only; no `aria-live` anywhere | build-workspace.tsx |
| `motion` still in `package.json` though nothing imports it | package.json |
| **`/build` mobile gated at 97, target 98.** True score ~97.5–98: after Next/React's own ~160 ms startup, the workspace's first full render is one more ~70–80 ms block (measured before any data is fetched). Close it by cutting that render, then set `minScore` back in `scripts/perf.mjs` | build-workspace.tsx, build-feed.tsx |
| `pnpm perf` is not automated (no CI yet) | — |

## PR gate

- [ ] At commit time: `pnpm check:changed` clean (the hook ran it; paste the output)
- [ ] At commit time, if `check:changed` said perf is due: `pnpm perf` passed (paste the summary)
- [ ] No billable call made automatically; writes guarded against double fire; no retry on writes
- [ ] Loading / empty / error states; server rules mirrored next to their control
- [ ] Late-arriving content cannot move anything above it; new skeletons match their final size
- [ ] Model output rendered as text; no prompt, brief or URL text in a route
- [ ] Theme tokens only — no new raw colours
- [ ] New `src/lib` logic has a test; nothing in Known gaps got worse, and any gap closed is removed from the table

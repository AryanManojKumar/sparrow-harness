# dsh-builder-03 — first B2B run of the agent-designed pipeline

2026-11-02. `b2b-tracewell`: API monitoring for platform teams, references
linear.app, vercel.com, resend.com. Whole pipeline through the office code
(`run.py`), gates answered as an owner with no files: wordmark, every image
generated, no video, drafted copy kept.

| | |
|---|---|
| Total | 53 min · ~$12.70 LLM (Azure has no prompt caching) |
| Groundwork (sources, design, content, assets) | 34 min · $2.37 |
| Agent build | 4 min · 14 calls · $2.01 |
| Fix round 1 | 12 min · 24 calls · $5.63 |
| Fix round 2 | stopped by hand at ~$2.70 — chasing "Details", "Logs", "Overview" |

The page reads beside Linear/Vercel: dark, exact, a trace walkthrough, the
generated dashboards placed as product shots, no invented customers or prices.
Weak: the generated dashboard images carry invented names ("Taylor Kim",
"acme.dev") — guardrails read code, not pixels — and the testimonial band is
filler.

## Findings

- **The build is cheap; the fixing was not.** Round 1 cost 2.8× the build: every
  call resent a ~50k-token build conversation, uncached, for one-line edits.
- **Claims cannot be auto-fixed well.** The check cannot tell a made-up latency
  in a drawn dashboard from a tab label.
- **Stalls, not sequencing, dominated the groundwork.** 5 of 34 calls sat
  137–377 s (timeout, then a retry that answered at once): ~24 of 34 minutes.
- Stopping a running agent: SIGTERM on the workshop waits for the open turn
  stream; it took `kill -9` to end the jailed runtime.

## Changed after this run

- Model calls are hedged: no answer by the usual time for that agent → a
  duplicate is sent and the first answer wins (`providers.hedged`).
- Sites are read, sections ranked and blueprints written concurrently
  (`steps.parallel`); measured 67 s for three site reads, was ~120 s.
- Verify auto-fixes only links, assets and brand distance, in a fresh short
  session without the look/polish pass; possible claims go to the owner at
  the preview gate and into the studio's suggestions.
- Still to do: build while images generate (placeholders) — ~2 min here, more
  with video.

@AGENTS.md

The whole frontend rulebook is `AGENTS.md`, imported above, so that Claude and every other
AI tool (which read `AGENTS.md`) follow the same rules. Do not add rules here; add them
there.

**Checks run at commit time only** (AGENTS.md › When the checks run). While working on a
change, do not run `pnpm check`, `pnpm perf`, builds, lint or format — write the code by
the rules. When asked to commit: if frontend files changed, run `pnpm check:changed` (changed files
only) and `pnpm perf` if it says perf is due; paste the output, fix failures, then commit.
Backend-only commits run no frontend checks. Never commit with `--no-verify`.

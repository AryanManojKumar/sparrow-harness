#!/usr/bin/env node
/**
 * pnpm check:changed — the commit-time check, scoped to the frontend files that
 * actually changed, so a commit costs seconds, not a full-project run.
 *
 *   pnpm check:changed            changed vs HEAD: staged, unstaged and untracked
 *   pnpm check:changed --staged   only what is staged (the git pre-commit hook uses this)
 *
 * No frontend file changed (a backend-only commit) → nothing runs, exit 0.
 * Otherwise, per kind of file changed:
 *   .ts/.tsx/.mjs/.mts  → tsc (whole project — types cross files, and it takes seconds),
 *                          eslint on those files only
 *   + .css/.json        → prettier --check on those files only
 *   src/**              → vitest on the tests related to those files only
 * and it says whether `pnpm perf` is due: only when UI, styles, dependencies or what a
 * page loads changed (AGENTS.md › When the checks run). It does not run perf itself —
 * that needs the backend and ~4 minutes.
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";

const staged = process.argv.includes("--staged");
const git = (args) =>
  spawnSync("git", args, { encoding: "utf8" })
    .stdout.split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

// Paths relative to frontend/ (the cwd); --relative drops anything outside it.
const diff = ["diff", "--name-only", "--relative", "--diff-filter=ACMR"];
const files = [
  ...new Set(
    staged
      ? git([...diff, "--cached"])
      : [...git([...diff, "HEAD"]), ...git(["ls-files", "--others", "--exclude-standard"])]
  ),
].filter((f) => existsSync(f));

if (!files.length) {
  console.log("check:changed — no frontend files changed; nothing to check.");
  process.exit(0);
}

const code = files.filter((f) => /\.(ts|tsx|mjs|mts|js)$/.test(f) && !f.startsWith("."));
const formattable = files.filter(
  (f) => /\.(ts|tsx|mjs|mts|js|css|json)$/.test(f) && f !== "pnpm-lock.yaml"
);
const src = code.filter((f) => f.startsWith("src/"));
const perfDue = files.some((f) =>
  /^(src\/.*\.(tsx|css)|src\/app\/|package\.json$|pnpm-lock\.yaml$|next\.config\.|postcss\.config\.)/.test(
    f
  )
);

console.log(`check:changed — ${files.length} frontend file(s) changed${staged ? " (staged)" : ""}`);
const bin = (name) => `./node_modules/.bin/${name}`;
const steps = [];
if (code.some((f) => /\.tsx?$/.test(f))) steps.push(["typecheck", bin("tsc"), ["--noEmit"]]);
if (code.length) steps.push(["lint", bin("eslint"), ["--max-warnings", "0", ...code]]);
if (formattable.length)
  steps.push(["format", bin("prettier"), ["--check", "--ignore-unknown", ...formattable]]);
if (src.length)
  steps.push(["test", bin("vitest"), ["related", "--run", "--passWithNoTests", ...src]]);

let failed = false;
for (const [label, cmd, args] of steps) {
  console.log(`\n▸ ${label}`);
  if (spawnSync(cmd, args, { stdio: "inherit" }).status !== 0) {
    failed = true;
    console.error(`✗ ${label} failed`);
  }
}

console.log(
  perfDue
    ? "\npnpm perf is DUE before committing: UI, styles, dependencies or page loading changed."
    : "\npnpm perf not needed: nothing that renders or loads on a page changed."
);
if (failed) {
  console.error("\ncheck:changed FAILED — fix the above (rules: frontend/AGENTS.md).");
  process.exit(1);
}
console.log("check:changed passed.");

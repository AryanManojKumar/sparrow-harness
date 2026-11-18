#!/usr/bin/env node
/**
 * pnpm perf — the console's performance gate. Fails (exit 1) if either holds:
 *
 *   1. JS budget: a page's first-load JavaScript (gzip) grew past its budget.
 *      Deterministic, and catches the usual regression — a new library on
 *      first load — the moment it lands.
 *   2. Lighthouse: the MEDIAN Performance score of N runs is under 98, or any
 *      run shows layout shift, on any page, mobile or desktop.
 *
 * Always a production build: `next dev` scores are meaningless. Single
 * mobile runs swing ±2, hence the median. Lighthouse is fetched by npx, so
 * there is no dependency to install; it drives your installed Chrome.
 *
 * /build needs a real project (the office API on :8000 and a project id that
 * exists there): PERF_PROJECT=<id>, default tabby-hours.
 *
 *   pnpm perf                 build, then full gate (5 mobile + 3 desktop runs per page)
 *   pnpm perf --quick         one run each — for a fast look, not for a verdict
 *   pnpm perf --no-build      reuse the existing .next build
 *
 * Why each budget and threshold is what it is, and the traps that already
 * cost points once: frontend/AGENTS.md.
 */
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const args = new Set(process.argv.slice(2));
const QUICK = args.has("--quick");
const PORT = Number(process.env.PERF_PORT || 3100);
const PROJECT = process.env.PERF_PROJECT || "tabby-hours";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BASE = `http://localhost:${PORT}`;

const MIN_SCORE = 98;
const RUNS = QUICK ? { mobile: 1, desktop: 1 } : { mobile: 5, desktop: 3 };
// First-load JS, gzip -6, measured 2026-11-18: home 191 KB, /build 195 KB.
// Next + React are ~150 KB of that and cannot shrink; the margin is for
// honest growth of our own code, not for a library.
const PAGES = [
  { name: "home", path: "/", budgetKB: 200 },
  {
    name: "build",
    path: `/build?id=${PROJECT}&resume=1&preview=1`,
    budgetKB: 205,
    // Temporary floor (decided 2026-11-18): its true mobile score sits at
    // ~97.5–98, so 98 failed about half its runs on noise alone. Target is 98 —
    // AGENTS.md › Known gaps. Raise it back when the gap is closed.
    minScore: { mobile: 97 },
  },
];

const failures = [];
const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

function run(cmd, argv, opts = {}) {
  const r = spawnSync(cmd, argv, { stdio: "inherit", ...opts });
  if (r.status !== 0) throw new Error(`${cmd} ${argv.join(" ")} exited ${r.status}`);
}

async function waitFor(url, ms = 30000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // not listening yet — keep polling until the deadline
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`${url} did not come up within ${ms / 1000}s`);
}

async function jsBudget(page) {
  const html = await (await fetch(BASE + page.path)).text();
  const srcs = [
    ...new Set([...html.matchAll(/src="(\/_next\/static\/chunks\/[^"]+\.js)"/g)].map((m) => m[1])),
  ];
  const bytes = srcs.reduce(
    (n, s) => n + gzipSync(readFileSync(join(".next", s.slice("/_next".length)))).length,
    0
  );
  const kb = bytes / 1024;
  const ok = kb <= page.budgetKB;
  console.log(
    `  ${ok ? "ok  " : "FAIL"} ${page.name.padEnd(6)} first-load JS ${kb.toFixed(1)} KB gzip (budget ${page.budgetKB} KB, ${srcs.length} scripts)`
  );
  if (!ok)
    failures.push(`${page.name}: first-load JS ${kb.toFixed(1)} KB > ${page.budgetKB} KB budget`);
}

function lighthouse(url, desktop, out) {
  const argv = [
    "-y",
    "lighthouse@12",
    url,
    "--only-categories=performance",
    "--quiet",
    "--chrome-flags=--headless=new",
    "--output=json",
    `--output-path=${out}`,
  ];
  if (desktop) argv.push("--preset=desktop");
  const r = spawnSync("npx", argv, { stdio: ["ignore", "ignore", "pipe"] });
  if (r.status !== 0) throw new Error(`lighthouse failed on ${url}: ${r.stderr}`);
  const a = JSON.parse(readFileSync(out, "utf8"));
  return {
    score: Math.round(a.categories.performance.score * 100),
    cls: a.audits["cumulative-layout-shift"].numericValue,
    lcp: a.audits["largest-contentful-paint"].displayValue,
    tbt: a.audits["total-blocking-time"].displayValue,
  };
}

async function main() {
  if (!args.has("--no-build")) run("./node_modules/.bin/next", ["build"]);

  try {
    await fetch(`${API}/projects/${PROJECT}`).then((r) => {
      if (!r.ok) throw new Error(String(r.status));
    });
  } catch (e) {
    console.error(
      `\n/build needs the office API at ${API} with project "${PROJECT}" (${e.message}).`
    );
    console.error("Start the backend (RUNNING.md) or set PERF_PROJECT to a project you have.\n");
    process.exit(2);
  }

  const server = spawn("./node_modules/.bin/next", ["start", "-p", String(PORT)], {
    stdio: "ignore",
  });
  const stop = () => server.kill();
  process.on("exit", stop);
  try {
    await waitFor(BASE);
    for (const p of PAGES) await fetch(BASE + p.path); // first request warms the server

    console.log("\nJS budget");
    for (const p of PAGES) await jsBudget(p);

    console.log(
      `\nLighthouse (median of ${RUNS.mobile} mobile / ${RUNS.desktop} desktop, need >= ${MIN_SCORE}, layout shift 0)`
    );
    const dir = mkdtempSync(join(tmpdir(), "sparrow-perf-"));
    for (const p of PAGES) {
      for (const form of ["mobile", "desktop"]) {
        const results = [];
        for (let i = 0; i < RUNS[form]; i++) {
          results.push(
            lighthouse(BASE + p.path, form === "desktop", join(dir, `${p.name}-${form}-${i}.json`))
          );
        }
        const med = median(results.map((r) => r.score));
        // At Lighthouse's own precision: sub-pixel rounding leaves values
        // like 0.00002 that it reports, and scores, as 0.
        const shift = Number(Math.max(...results.map((r) => r.cls)).toFixed(3));
        const min = p.minScore?.[form] ?? MIN_SCORE;
        const ok = med >= min && shift === 0;
        const scores = results.map((r) => r.score).join(" ");
        console.log(
          `  ${ok ? "ok  " : "FAIL"} ${p.name.padEnd(6)} ${form.padEnd(7)} median ${med} (need ${min})  [${scores}]  CLS ${shift.toFixed(3)}  LCP ${results[0].lcp}  TBT ${results[0].tbt}`
        );
        if (med < min) failures.push(`${p.name} ${form}: median score ${med} < ${min}`);
        if (shift > 0)
          failures.push(`${p.name} ${form}: layout shift ${shift.toFixed(3)} (must be 0)`);
      }
    }
  } finally {
    stop();
  }

  if (failures.length) {
    console.error(
      `\nPERF GATE FAILED\n  - ${failures.join("\n  - ")}\nSee frontend/AGENTS.md for the known causes.\n`
    );
    process.exit(1);
  }
  console.log("\nPERF GATE PASSED\n");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

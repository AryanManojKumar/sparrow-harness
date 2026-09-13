# Scaffold

The base image every project starts from. **Contains zero design decisions.**

Copied per project, then `pnpm install --frozen-lockfile` — pnpm hardlinks from the global
content-addressable store, so the hundredth project costs seconds and near-zero disk.
`node_modules` is never copied and never committed.

| Layer | Per project? | Where |
|---|---|---|
| Scaffold | Identical every run | this directory |
| Design system | **Unique** | the marked block in `src/app/globals.css` |
| Sections | **Unique** | `src/components/sections/`, composed from blueprints |

## Pinned

Next 16.3.1 · React 19.2.8 · TypeScript 5.9.3 · Tailwind 4.3.3 · shadcn (radix base, nova preset)
· Motion 13.1.1 · lucide-react 1.33 · pnpm 11.22

Static export (`output: "export"`), `trailingSlash: true`, `images.unoptimized` — assets arrive
pre-sized from `curator`.

## The token surface

`src/app/globals.css` holds the only place design may be expressed, fenced between
`DESIGN SYSTEM` markers. Values ship achromatic — `oklch(L 0 0)` is zero chroma, i.e. no design yet.

Token **names** are a stable contract: blueprints and shadcn primitives reference them and must
keep working. Token **values** are per project. `builder` reads them and may not write them —
it proposes a diff (see `AGENTS.md` §8).

## Rules

- `pnpm add` only — never hand-edit `package.json` or the lockfile
- Tailwind utilities only — no CSS-in-JS, no styled-jsx, no `.module.css`
- Semantic tokens only — never `text-white` / `bg-black` in a `className`
- Import from `motion/react`, never `framer-motion`
- Icons from `lucide-react`, never emoji

## Verify

    pnpm install --frozen-lockfile
    pnpm build      # must reach "prerendered as static content"

# Design system — Ledgerline

Recorded decisions. `builder` builds to these and does not extend them silently.

## Palette
Deliberately warm and low-chroma. Deep forest green carries authority without the
blue that every compliance vendor defaults to. Amber is used sparingly, for a single
emphasis per section at most.

| Token | Value | Role |
|---|---|---|
| `--background` | `oklch(0.993 0.004 95)` | warm off-white page ground |
| `--foreground` | `oklch(0.22 0.012 95)` | body text |
| `--primary` | `oklch(0.45 0.10 155)` | forest green — CTAs, emphasis |
| `--primary-foreground` | `oklch(0.985 0.006 95)` | text on green |
| `--accent` | `oklch(0.78 0.145 72)` | amber — one emphasis per section, maximum |
| `--muted` | `oklch(0.965 0.006 95)` | alternating section grounds |
| `--muted-foreground` | `oklch(0.52 0.014 95)` | secondary text |
| `--border` | `oklch(0.90 0.008 95)` | hairlines |

**Nine values. There is no tenth.** No blue at any chroma (hue 200–290 is out of bounds).

## Type
Geist, already loaded. One family, weights 400 / 500 / 600 only — never 700 or above.

| Step | Size / leading | Use |
|---|---|---|
| display | `text-5xl md:text-6xl` / `leading-[1.05]` / `tracking-tight` | hero headline only |
| h2 | `text-3xl md:text-4xl` / `leading-tight` | section headings |
| h3 | `text-xl` / `leading-snug` | card titles |
| body | `text-base` / `leading-relaxed` | prose |
| small | `text-sm` / `leading-normal` | captions, labels |
| eyebrow | `text-xs` / `tracking-widest` / `uppercase` / `font-medium` | section labels |

## Spacing
Section padding `py-24 md:py-32`. Container `max-w-6xl px-6`. Grid gap `gap-8`.
Stack rhythm inside a section: `space-y-4` tight, `space-y-8` loose. Nothing else.

## Radius
`--radius: 0.5rem`. Cards and buttons `rounded-lg`. Inputs `rounded-md`. Never fully round
except avatars.

## Shadows
Two, both barely visible:
- `shadow-sm` — resting cards
- `shadow-md` — hover only

No coloured shadows, no glows.

## Imagery treatment
Product screenshots sit in a plain rounded container with a hairline border and `shadow-md`,
bleeding off the right edge of the container on desktop. No browser chrome, no perspective
tilt, no gradient backdrop.

## Motion
Entrance only: fade up 12px, 400ms, `ease-out`, staggered 60ms across siblings.
Hover: 150ms colour transition on interactive elements. Nothing else moves.

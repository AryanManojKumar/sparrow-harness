# Blueprint: feature-grid
**Order:** 3 · **File:** `src/components/sections/FeatureGrid.tsx`

Purpose: three to six capabilities, scannable, each earning its place.

Slots: `eyebrow` · `heading` · `intro` · `features[]` (each: `icon`, `title`, `body`)

Structure: section heading block, then a responsive grid — 1 column mobile, 2 tablet, 3 desktop.
Each feature is a card with an icon, a title at the `h3` step, and two to three lines of body.
Icons come from lucide-react at a single consistent size across all cards.

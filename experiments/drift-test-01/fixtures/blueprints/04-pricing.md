# Blueprint: pricing
**Order:** 4 · **File:** `src/components/sections/Pricing.tsx`

Purpose: three tiers, with the middle one recommended.

Slots: `eyebrow` · `heading` · `tiers[]` (each: `name`, `price`, `cadence`, `summary`,
`features[]`, `cta`, `recommended?`)

Structure: heading block, then three columns of equal height — stacking on mobile. The
recommended tier is distinguished by exactly one visual device, chosen by the builder, and is
the only element in the section allowed to use the accent colour. Feature lists use a check
icon from lucide-react. Every tier's CTA sits on the same baseline regardless of list length.

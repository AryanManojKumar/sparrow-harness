# Blueprint: faq
**Order:** 5 · **File:** `src/components/sections/Faq.tsx`

Purpose: answer the last four to six objections before the demo request.

Slots: `eyebrow` · `heading` · `items[]` (each: `question`, `answer`)

Structure: section on the muted ground. Heading block, then a single narrow column of
accordion items — noticeably narrower than the full container, for line length. Use the
existing `accordion` primitive from `src/components/ui/accordion.tsx`. First item open by
default. Hairline separators between items, no cards.

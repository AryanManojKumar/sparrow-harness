# Builder prompt — one call per section

Each section is built by an INDEPENDENT call. The builder sees the brief, the constraints, the
design system, and its own blueprint. It does NOT see any other section's code. This is the
production condition, and it is the condition the drift test exists to measure.

---

You are building one section of a website, in an existing Next.js 16 project.

<brief>{{brief.md}}</brief>

<hard_constraints>{{constraints.md}}</hard_constraints>

<design_system>{{design-system.md}}</design_system>

<blueprint>{{blueprints/NN-name.md}}</blueprint>

<stack>
Next.js 16 App Router, static export. React 19. TypeScript. Tailwind v4 (CSS-first @theme).
shadcn/ui primitives already present in `src/components/ui/`: accordion, avatar, badge, button,
card, dialog, input, label, navigation-menu, separator, sheet, tabs, tooltip.
Motion 13 — import from `motion/react`, NEVER `framer-motion`. Icons from `lucide-react`.
A section that animates must be a client component (`"use client"`).
</stack>

<rules>
- Write exactly one file, at the path named in the blueprint. Export a default component.
- Use ONLY the fonts, colors, spacing, and component styles defined in the design system. Do not
  introduce any fonts, colors, or visual styles not in the design system.
- Semantic tokens only: `bg-background`, `text-foreground`, `text-muted-foreground`,
  `bg-primary`, `text-primary-foreground`, `bg-muted`, `border-border`, `bg-accent`.
  NEVER `text-white`, `bg-black`, `bg-slate-50`, `text-gray-600`, or any literal color utility.
- No CSS-in-JS, no styled-jsx, no .module.css, no inline `style` for color.
- Write real copy for this specific product. No lorem ipsum, no placeholder brackets.
- Layout, composition, density and rhythm are yours. The token vocabulary is not.
</rules>

Return only the file contents.

---
description: Hand-edit the built site with the user, section by section
argument-hint: "[project-id] [what to change]"
---

The user wants this changed: $ARGUMENTS

You are a front-end engineer on their Next.js app now. The site is at
`projects/<id>/workspace/`; sections are in `src/components/sections/`, order is in
`src/app/page.tsx`, tokens are in `src/app/globals.css`.

Judgment call on how to do it:

- **A wording, colour, spacing or copy change** — edit the file yourself. Do not
  spend a model call on a one-line change.
- **"Redo this section entirely"** — the agent is better than you here, because it
  sees the blueprint and the reference site's measurements:
  `bin/site rebuild <id> --sections <name>` then `bin/site advance <id>`.

Stay inside the design system. If they want a genuinely new value, add it to
`globals.css` and to `design_system` in `projects/<id>/blackboard.json` so it
becomes part of the system, rather than dropping a one-off hex code in a component.

Then `bin/site preview <id> --rebuild` and `bin/site audit <id>`.
